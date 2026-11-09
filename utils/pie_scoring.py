"""PIE's processed arrays, the development-fold splits, prediction files, and PIE's metric code.

`load` reads a dir in the format `pie prep` writes (meta.json plus .npy arrays): PIE's released Replogle–Nadig arrays
(pie_benchmark/preprocessed) and perturbseq/processed/<dataset>/preprocessed. `pie_metrics` calls PIE's own metric code
(ArcInstitute/pie @ 21a526a), so it needs the `pie` package: PIE's environment, or PIE's `src/` on PYTHONPATH in this
repository's environment. Everything else runs without it.
"""

import json
import pathlib
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

FDR = 0.05  # data.fdr_threshold in PIE's configs/train.yaml
METRICS = ["binary_auprc", "sig_jaccard", "direction_match", "spearman_nsig", "spearman_lfc", "discrimination_score_l1"]


def load(path):
    """A preprocessed dir, one row per (context, knockdown): delta_p, DE calls at FDR 0.05 among tested genes, LFC
    (NaN where untested), and `own`, the readout column of each row's knocked-down gene (-1 if it is not a readout)."""
    path = pathlib.Path(path)
    meta = json.loads((path / "meta.json").read_text())
    a = lambda name: np.load(path / f"{name}.npy", mmap_mode="r")  # noqa: E731
    d = SimpleNamespace(name=meta["dataset"], genes=list(meta["genes"]), ctx_ids=a("ctx_ids"), tested=a("tested"),
                        lfc=a("lfc_true"), delta=a("delta_p"), ctrl=a("ctrl_means"))
    d.de = (a("fdr") < FDR) & d.tested  # as pie.evaluate.scoring_inputs
    d.context = np.array(sorted(meta["context_to_id"], key=meta["context_to_id"].get))[d.ctx_ids]
    d.pert = np.array(sorted(meta["pert_to_id"], key=meta["pert_to_id"].get))[a("pert_ids")]
    col = {g: j for j, g in enumerate(d.genes)}
    by_id = {}
    if (path / "axis_map.parquet").exists():  # each readout's gene id, as K062's prep writes it (columns axis, readout)
        axis = pd.read_parquet(path / "axis_map.parquet")
        assert axis.axis.tolist() == d.genes, "axis_map.parquet is not in the order of meta.json's genes"
        by_id = {g: j for j, g in enumerate(axis.readout)}
    # by Ensembl id first, as K062 did: some targets keep an old symbol (GARS is the readout GARS1)
    ensembl = meta.get("pert_ensembl", {})
    d.own = np.array([by_id.get(ensembl.get(p), col.get(p, -1)) for p in d.pert])
    return d


def responses(d, rows):
    """delta_p of these rows with each knockdown's own gene set to 0, as PWPA was fitted (ext_score's loader)."""
    X = np.array(d.delta[rows], np.float32)
    i = np.flatnonzero(d.own[rows] >= 0)
    X[i, d.own[rows][i]] = 0
    return X


def split(splits, fold):
    """Development fold `fold` of a splits table (0.datasets/splits: symbol, fold), as knocked-down gene symbols, PIE's
    perturbation names: test = the fold's genes, validation = 20% of the other development folds' genes, train = the
    rest. Fold 4 is never read. The draw is K062-pie-eight/data.py's (sorted genes, numpy default_rng(0) permutation),
    as 3.split_genes.ipynb and 1.train_pie.ipynb, so PWPA and PIE stop on the same validation genes."""
    dev = splits[splits.fold.isin(range(4))]
    genes = np.sort(dev.symbol[dev.fold != fold].unique())
    val = np.random.default_rng(0).permutation(genes)[: round(0.2 * len(genes))]
    return {"train": np.setdiff1d(genes, val), "val": np.sort(val), "test": np.sort(dev.symbol[dev.fold == fold].unique())}


def write_predictions(path, d, rows, p_de, lfc, delta):
    """Predictions for these rows of d in the parquet format of PIE's pie.predict.write_predictions_parquet."""
    lists = [pa.array(list(np.asarray(x, np.float32)), pa.list_(pa.float32())) for x in (p_de, lfc, delta)]
    table = pa.table([pa.array([d.name] * len(rows)), pa.array(d.context[rows].tolist()), pa.array(d.pert[rows].tolist()), *lists],
                     names=["dataset", "context", "perturbation", "p_de", "lfc_pred", "delta_p_pred"])
    meta = {"pie": json.dumps({"format_version": 1, "genes": {d.name: d.genes}})}
    pq.write_table(table.replace_schema_metadata(meta), path)


def read_predictions(path, d):
    """The rows of d that a predictions parquet covers, and its p_de, lfc_pred and delta_p_pred arrays."""
    table = pq.read_table(path)
    assert json.loads(table.schema.metadata[b"pie"])["genes"][d.name] == d.genes, f"{path}: gene axis differs from {d.name}"
    p = table.to_pandas()
    index = {k: i for i, k in enumerate(zip(d.context, d.pert))}
    rows = np.array([index[k] for k in zip(p.context, p.perturbation)])
    return rows, *(np.stack(p[c].values) for c in ("p_de", "lfc_pred", "delta_p_pred"))


def pie_metrics(d, rows, p_de, lfc, delta):
    """PIE's six metrics of predictions for these rows of d: the mean over contexts, NaN skipped (the 'all' row of
    PIE's metrics_table)."""
    return pd.Series(_score(d, rows, p_de, lfc, delta).context_mean)[METRICS].astype(float)  # = the 'all' row of pie.evaluate.metrics_table


def pair_auprc(d, rows, p_de, lfc, delta):
    """PIE's AUPRC of each (context, knockdown): a Series on that MultiIndex. Its mean per context, then over contexts,
    is pie_metrics' binary_auprc."""
    pairs = _score(d, rows, p_de, lfc, delta).per_pair
    return pairs.set_index(["context", "perturbation"]).binary_auprc.astype(float)


def bootstrap(*pairs, n=1000, seed=0):
    """95% intervals of PIE's AUPRC (mean over contexts of the mean over knockdowns) from pair_auprc Series, resampling
    knockdowns within each context. Several Series on the same pairs share the resamples, so the interval of their
    difference is paired. Returns (n, len(pairs)) resampled AUPRCs; take np.percentile(..., [2.5, 97.5], axis=0)."""
    table = pd.concat(pairs, axis=1, join="inner")
    rng = np.random.default_rng(seed)
    out = 0
    groups = [g.to_numpy() for _, g in table.groupby(level="context")]
    for g in groups:
        out = out + g[rng.integers(0, len(g), (n, len(g)))].mean(1) / len(groups)
    return out


def _score(d, rows, p_de, lfc, delta):
    try:  # PIE's code, imported here so that loading works without PIE
        from pie.metrics import ScoringInputs, score
    except ModuleNotFoundError as e:
        if e.name != "pydantic":
            raise
        # this environment has no pydantic, which pie.data.preprocessed needs; pie.metrics uses one function of it,
        # copied from PIE @ 21a526a (src/pie/data/preprocessed.py)
        stub = sys.modules["pie.data.preprocessed"] = ModuleType("pie.data.preprocessed")
        stub.target_gene_index = lambda perturbation, gene_index: int(gene_index.get(perturbation, -1))
        from pie.metrics import ScoringInputs, score

    rows = np.asarray(rows)
    return score([ScoringInputs(
        dataset=d.name, genes=d.genes, contexts=d.context[rows].tolist(), perts=d.pert[rows].tolist(),
        p_de=np.asarray(p_de, np.float32), lfc_pred=np.asarray(lfc, np.float32), delta_p_pred=np.asarray(delta, np.float32),
        de_true=d.de[rows], tested=np.asarray(d.tested[rows], bool), lfc_true=np.asarray(d.lfc[rows], np.float64),
        delta_p_true=np.asarray(d.delta[rows], np.float32), ctrl_means=np.asarray(d.ctrl, np.float32)[d.ctx_ids[rows]],
    )])
