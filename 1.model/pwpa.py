"""PWPA, the Prior-Weighted Partner Average.

A knockdown t that was not measured in a context is predicted from the knockdowns j that were:

    score(t, j)   = sum_d gate_d * z_d(t, j)     z_d: prior d's similarity, z-scored over the training pairs
    weight(t, .)  = entmax15(score(t, .))         sparse, sums to 1; t's own knockdown gets weight 0
    prediction(t) = sum_j weight(t, j) * response(j)

The gates, one per prior and never negative, are the only fitted numbers. With every gate at 0 the weights are equal
and the prediction is the mean training knockdown. `rfe` and `choose` pick which priors to keep.

A prior is a function (genes_a, genes_b) -> (similarity, covered), two arrays of shape (len(genes_a), len(genes_b)).
`load_priors` reads the priors that 0.build_priors.ipynb writes.

Self-check on synthetic priors: python pwpa.py
"""

import pathlib

import numpy as np
import pandas as pd
import scipy.sparse as sp
import torch
from entmax import entmax15

# the original fit's settings (immune_grn/lab/exp/F018-sparse-mlp-attention/arm.py, H002-linear-gated/gated.py)
SEEDS = range(5)  # each seed holds out a different 25% of the training genes
STEPS = 3000
EVAL_EVERY = 10
PATIENCE = 400
LR = 3e-3  # Adam, no weight decay
N_PANEL = 300  # the loss is taken on the genes that respond most across the training knockdowns


def profile_prior(rows):
    """A prior from one row per gene (DataFrame, genes x features): similarity = dot product of the two rows.
    A pair is covered when both genes have a row."""

    def prior(a, b):
        fa, fb = (rows.reindex(g).fillna(0).to_numpy(np.float32) for g in (a, b))
        return fa @ fb.T, np.isin(a, rows.index)[:, None] & np.isin(b, rows.index)[None, :]

    return prior


def network_prior(edges):
    """A prior from weighted edges (DataFrame: gene_a, gene_b, weight). A missing edge is similarity 0, so every
    pair is covered."""
    # both directions, one weight per pair (the largest when a pair is listed twice)
    both = pd.concat([edges, edges.rename(columns={"gene_a": "gene_b", "gene_b": "gene_a"})])
    both = both.groupby(["gene_a", "gene_b"], as_index=False).weight.max()
    genes = pd.Index(pd.unique(both.gene_a))
    m = sp.coo_matrix(
        (both.weight, (genes.get_indexer(both.gene_a), genes.get_indexer(both.gene_b))), shape=(len(genes),) * 2
    ).tocsr()

    def prior(a, b):
        ia, ib = genes.get_indexer(a), genes.get_indexer(b)
        sim = np.zeros((len(a), len(b)), np.float32)
        ka, kb = ia >= 0, ib >= 0
        sim[np.ix_(ka, kb)] = m[ia[ka]][:, ib[kb]].toarray()
        return sim, np.ones(sim.shape, bool)

    return prior


def load_priors(root):
    """{name: prior} for every file in root/profile (genes x features) and root/network (gene_a, gene_b, weight)."""
    root = pathlib.Path(root)
    priors = {p.stem: profile_prior(pd.read_parquet(p)) for p in sorted((root / "profile").glob("*.parquet"))}
    priors |= {p.stem: network_prior(pd.read_parquet(p)) for p in sorted((root / "network").glob("*.parquet"))}
    return priors


def similarities(priors, a, b):
    """(len(a), len(b), n_priors) similarities and the pairs each prior covers."""
    sims, covered = zip(*(prior(a, b) for prior in priors))
    return np.stack(sims, -1), np.stack(covered, -1)


def fit_scale(priors, gene_sets):
    """Each prior's mean and sd over the training pairs it covers, pooled over contexts, without a gene and itself."""
    pairs = [[] for _ in priors]
    for genes in gene_sets:
        S, C = similarities(priors, genes, genes)
        C &= (genes[:, None] != genes[None, :])[..., None]
        for d in range(len(priors)):
            pairs[d].append(S[..., d][C[..., d]])
    pairs = [np.concatenate(p) for p in pairs]
    mu, sd = (np.array([f(p) for p in pairs], np.float32) for f in (np.mean, np.std))
    assert (sd > 0).all(), "a prior is constant over the training pairs; leave it out"
    return mu, sd


def standardise(S, C, scale):
    """z-score each prior with its training mean and sd; an uncovered pair is 0, the average pair."""
    mu, sd = scale
    return torch.from_numpy(np.where(C, (S - mu) / sd, 0).astype(np.float32))


def weights(Z, gates, own=None):
    """Partner weights: entmax15 over the partners of Z @ gates. `own` marks a gene paired with itself (weight 0)."""
    score = Z @ gates
    if own is not None:  # 10 below the row's lowest real score: always outside entmax-1.5's support
        low = score.detach().masked_fill(own, torch.inf).min(-1, keepdim=True).values - 10
        score = torch.where(own, low, score)
    return entmax15(score, dim=-1)


def fit(priors, contexts, scale, seeds=SEEDS):
    """Fit the gates. `contexts` has one (genes, responses) pair per cell state: the training knockdowns' genes (n,) and
    responses (n, n_readouts). One gate vector serves every context. Each seed holds out 25% of the genes (the same
    genes in every context), predicts them from the other genes, and keeps the gates with the lowest held-out loss.
    Returns the gates (n_seeds, n_priors) and the held-out losses (n_seeds,)."""
    blocks = []
    for genes, R in contexts:
        panel = np.argsort(-np.abs(R).mean(0))[:N_PANEL]  # from every training gene, held-out ones included, as the original fit
        Z = standardise(*similarities(priors, genes, genes), scale)
        blocks.append((genes, Z, torch.from_numpy(R[:, panel].astype(np.float32))))
    all_genes = np.unique(np.concatenate([g for g, _ in contexts]))
    fitted, losses = [], []
    for seed in seeds:
        held = all_genes[np.random.default_rng(seed).permutation(len(all_genes)) % 4 == 0]
        sets = []
        for genes, Z, R in blocks:
            h = np.isin(genes, held)
            own = torch.from_numpy(genes[~h, None] == genes[None, ~h])
            sets.append((Z[~h][:, ~h], own, Z[h][:, ~h], R[~h], R[h]))
        gates = torch.zeros(len(priors), requires_grad=True)
        opt = torch.optim.Adam([gates], lr=LR)

        def loss(held_out):
            err = [
                ((weights(Zh, gates) @ Rk - Rh) ** 2).mean(1) if held_out else ((weights(Zk, gates, own) @ Rk - Rk) ** 2).mean(1)
                for Zk, own, Zh, Rk, Rh in sets
            ]
            return torch.cat(err).mean()

        best = (np.inf, 0, gates.detach().clone())
        for step in range(STEPS):
            if step % EVAL_EVERY == 0:
                with torch.no_grad():
                    held_loss = loss(True).item()
                if held_loss < best[0]:
                    best = (held_loss, step, gates.detach().clone())
                elif step - best[1] > PATIENCE:
                    break
            opt.zero_grad()
            loss(False).backward()
            opt.step()
            with torch.no_grad():
                gates.clamp_(min=0)
        losses.append(best[0])
        fitted.append(best[2])
    return torch.stack(fitted), np.array(losses)


def predict(priors, scale, gates, genes, partners, responses):
    """Predict `genes` from the measured `partners` of one context (their genes and responses): the partner weights,
    averaged over seeds, times the partners' responses. Returns the predictions and the weights."""
    genes, partners = np.asarray(genes), np.asarray(partners)
    Z = standardise(*similarities(priors, genes, partners), scale)
    own = torch.from_numpy(genes[:, None] == partners[None, :])
    with torch.no_grad():
        W = torch.stack([weights(Z, g, own) for g in gates]).mean(0).numpy()
    return W @ responses, W


def predict_de(W, de, lfc, own=None, tested=None):
    """PIE's DE probability and fold change for each predicted row, from the partner weights W (n, n_partners) and
    the partners' DE calls `de` (bool) and fold changes `lfc` (n_partners, n_readouts; NaN where untested).
    s = W @ de is the weighted share of partners that call a gene DE. Each row calls as many genes as its partners do
    (weighted average), and p_de rescales s so that exactly those genes reach 0.5, PIE's call threshold. A gene's fold
    change is its average over the partners that call it DE, or over all partners when none does.
    own[j]: the readout column of partner j's own knocked-down gene, or -1; that entry takes the other partners' mean.
    tested: the readouts that can be called (default all). As K062-pie-eight/score_all.py, option A."""
    de, lfc = de.astype(np.float64), lfc.astype(np.float64)
    lfc = np.where(np.isnan(lfc), np.nan_to_num(np.nanmean(lfc, 0)), lfc)
    n_de = de.sum(1)
    for j, t in enumerate(own if own is not None else []):
        if t >= 0:
            others = np.delete(np.arange(len(de)), j)
            n_de[j] -= de[j, t]
            de[j, t], lfc[j, t] = de[others, t].mean(), lfc[others, t].mean()
    tested = np.ones(de.shape[1], bool) if tested is None else tested
    s, n = W @ de, np.rint(W @ n_de / W.sum(1)).astype(int)
    p_de = np.empty_like(s)
    for i in range(len(s)):
        top = np.sort(s[i, tested])[::-1]
        m = min(n[i], int((top > 0).sum()))
        x = s[i] / (top[m - 1] if m > 0 else 2 * max(s[i].max(), 1e-12))
        p_de[i] = x / (1 + x)
    fold = np.where(s > 1e-12, (W @ (de * lfc)) / np.maximum(s, 1e-12), W @ lfc)
    return p_de, fold


def rfe(priors, contexts):
    """Recursive feature elimination over the priors ({name: prior}): fit all gates, drop the prior with the smallest
    gate, refit, until one prior is left. Returns the path, one dict per step: priors kept, gates, scale, losses."""
    names = list(priors)
    full_scale = fit_scale(list(priors.values()), [g for g, _ in contexts])
    kept, path = list(range(len(names))), []
    while kept:
        scale = tuple(s[kept] for s in full_scale)
        gates, losses = fit([priors[names[i]] for i in kept], contexts, scale)
        path.append({"priors": [names[i] for i in kept], "gates": gates, "scale": scale, "losses": losses})
        kept.pop(int(gates.mean(0).argmin()))
    return path


def choose(path):
    """The smallest set whose held-out loss is within one standard error (over seeds) of the fit on all priors.
    R032-marson-rfe chose the size from development test scores; this uses only the training genes' held-out loss,
    the rule R031-replogle-rfe intended, so no test row decides the model."""
    full = path[0]["losses"]
    bar = full.mean() + (full.std(ddof=1) / np.sqrt(len(full)) if len(full) > 1 else 0)
    return min((p for p in path if p["losses"].mean() <= bar), key=lambda p: len(p["priors"]))


if __name__ == "__main__":  # self-check on synthetic priors
    rng = np.random.default_rng(0)
    genes = np.array([f"g{i}" for i in range(90)])
    latent = rng.normal(size=(90, 4))  # drives the responses and the informative prior
    priors = {
        "informative": profile_prior(pd.DataFrame(latent + 0.5 * rng.normal(size=(90, 4)), index=genes)),
        "noise": profile_prior(pd.DataFrame(rng.normal(size=(90, 4)), index=genes)),
    }
    responses = (latent @ rng.normal(size=(4, 400)) + rng.normal(size=(90, 400))).astype(np.float32)
    train, test = genes[:70], genes[70:]

    path = rfe(priors, [(train, responses[:70])])
    gates, scale = path[0]["gates"], path[0]["scale"]
    assert (gates >= 0).all() and (gates[:, 0] > gates[:, 1]).all(), gates
    assert path[-1]["priors"] == ["informative"] and choose(path) in path

    pred, W = predict(list(priors.values()), scale, gates, test, train, responses[:70])
    assert np.allclose(W.sum(1), 1, atol=1e-5)
    mean_knockdown = responses[:70].mean(0)
    assert ((pred - responses[70:]) ** 2).mean() < ((mean_knockdown - responses[70:]) ** 2).mean()

    # every gate 0: equal weights over the other knockdowns, so the prediction is their mean
    pred0, W0 = predict(list(priors.values()), scale, torch.zeros(1, 2), train[:1], train, responses[:70])
    assert W0[0, 0] == 0 and np.allclose(W0[0, 1:], 1 / 69, atol=1e-6)
    assert np.allclose(pred0[0], responses[1:70].mean(0), atol=1e-4)

    de = np.abs(responses[:70]) > 2
    p_de, fold = predict_de(W, de, responses[:70])
    assert ((p_de >= 0) & (p_de < 1)).all() and ((p_de >= 0.5).sum(1) == np.rint(W @ de.sum(1))).all()
    print("pwpa.py self-check ok:", [(p["priors"], p["losses"].mean().round(3)) for p in path])
