"""Marson CD4+ T cells (Zhu et al. 2026) for 3.further_analysis: the pseudobulk responses that
0.datasets/2.process_perturbseq.ipynb writes, PIE's five priors looked up for Marson's genes, and PWPA fitted once on
every knockdown."""

import json
import sys

import numpy as np
import pandas as pd
import torch

from paths import REPO, data_dir

sys.path.append(str(REPO / "1.model"))
import pwpa

STATES = ("Rest", "Stim8hr", "Stim48hr")


def load():
    """obs: one row per state x knockdown (key, ensg, symbol, condition, target_col = the knocked-down gene's readout
    column or -1, fold); delta: each row's mean log1p expression minus the state's non-targeting mean, own column 0;
    readouts: the readout genes; symbols: {ensg: symbol} of every gene the screen targeted."""
    d = data_dir("perturbseq", "processed", "marson")
    obs = pd.read_parquet(d / "obs.parquet")
    folds = pd.read_csv(REPO / "0.datasets" / "splits" / "marson.tsv", sep="\t").set_index(["context", "ensg"]).fold
    obs["fold"] = folds.reindex(pd.MultiIndex.from_arrays([obs.condition, obs.ensg])).values
    assert obs.fold.notna().all()
    delta = np.load(d / "delta.npy")
    own = np.flatnonzero(obs.target_col.values >= 0)
    delta[own, obs.target_col.values[own]] = 0  # the knocked-down gene's own readout says nothing about regulation
    return obs, delta, np.load(d / "genes.npy").astype(str), json.loads((d / "symbols.json").read_text())


def priors(symbols):
    """PIE's five genetic sources (1.model/0.build_priors.ipynb), which index genes by symbol, for Marson's ENSG ids.
    A gene without a symbol, or missing from a source, is uncovered there. Genes stay ENSG ids everywhere else, so two
    ids that shared a symbol would share its rows but remain two genes."""
    name = lambda genes: np.array([symbols.get(g) or "" for g in genes])  # noqa: E731
    return {n: (lambda a, b, p=p: p(name(a), name(b))) for n, p in pwpa.load_priors(data_dir("priors")).items()}


def contexts(obs, delta, rows):
    """pwpa's contexts from the rows of obs selected by the boolean mask `rows`: (genes, responses) per state."""
    return [(obs.ensg.values[m], delta[m]) for m in (rows & (obs.condition == s).values for s in STATES)]


def final_model(priors):
    """PWPA fitted once on every knockdown, the lockbox fold included (M001-pwpa-final-grn), for analysis only and never
    scored. RFE picks the priors; with no validation split, each of 5 seeds stops early on a different 25% of the
    genes. Saved on first use, so that every notebook here explains the same fit."""
    path = data_dir("predictions", "pwpa", "marson_all") / "model.pt"
    if not path.exists():
        obs, delta, _, _ = load()
        torch.save(pwpa.choose(pwpa.rfe(priors, contexts(obs, delta, np.ones(len(obs), bool)))), path)
    return torch.load(path, weights_only=False)


def panel(responses):
    """The 300 readouts with the largest mean |change| over these knockdowns."""
    return np.argsort(-np.abs(responses).mean(0))[:300]
