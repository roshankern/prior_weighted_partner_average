# 2.train_test

This module trains PWPA and PIE and scores both with PIE's metric code.

| Notebook | What it does |
|---|---|
| [`0.pie_benchmark.ipynb`](0.pie_benchmark.ipynb) | Train and score PWPA on PIE's Replogle–Nadig benchmark, next to the values in PIE's paper |
| [`1.train_pie.ipynb`](1.train_pie.ipynb) | Train PIE on each fold of eight Perturb-seq datasets (GPU, PIE's environment) |
| [`2.train_pwpa.ipynb`](2.train_pwpa.ipynb) | Train PWPA on the same folds |
| [`3.score_eight_datasets.ipynb`](3.score_eight_datasets.ipynb) | Score the context mean, PIE and PWPA, and draw the eight-dataset figure |

[`results/`](results/) holds the scores behind the figures in tidy long format, one row per dataset, model and metric.

## Metrics

All scores come from PIE's metric code at FDR 0.05.
AUPRC and Jaccard measure which genes are called DE.
DE direction match measures which way they move.
Spearman effect size compares how many genes each knockdown moves.
Spearman LFC compares fold changes.
Discrimination L1 measures whether a prediction is closest to its own knockdown.
The context mean, the baseline, predicts the mean training knockdown of the context for every test knockdown.

## PIE's benchmark

<!-- TODO(orcd): PWPA here is K031-pie-five, fitted with the earlier L1 penalty and shuffled decoys; rerun 0.pie_benchmark.ipynb with RFE -->
![PIE benchmark](figures/main_figure.png)

> Unseen knockdowns in seen contexts (Replogle–Nadig, four cell lines), with PIE's processed arrays, splits and metric code.
> The first five bars are PIE's published values.
> PWPA uses PIE's five genetic knowledge sources as its priors, the same gene information PIE gets.

## Eight datasets

<!-- TODO(orcd): PWPA bars are from gates fitted on PIE's five genetic sources without RFE; rerun 2.train_pwpa.ipynb -->
![PIE and PWPA on eight datasets](figures/eight_datasets.png)

> Every dataset goes through PIE's pipeline before any model sees it, and every model gets the same training, validation and test knockdowns.
> PIE is retrained on each dataset with its own recipe and all of its own inputs.
> Mean over development folds 0–3, ± 1 standard error.
> PWPA again uses PIE's five genetic knowledge sources (the figure calls them matched priors).
> Marson T cells are left out because PIE's pipeline needs cell-level counts, and this repository uses Marson's pseudobulk counts.

\* Shi: in vivo data from 74 mice. The labels use PIE's cell-level DE, which treats each cell as a replicate and ignores mouse-to-mouse variation.
† Geiger-Schuller: primary mouse dendritic cells in 16 hashtagged samples over 2 rounds. Cell-level DE ignores this sample structure.
‡ Nourreddine: each knockdown was screened in one of three batches, but cell-level DE compares it with non-targeting cells pooled across all batches, so batch differences can enter the labels.

## Environments

PWPA uses this repository's environment.
PIE uses its own, built from [ArcInstitute/pie](https://github.com/ArcInstitute/pie) at commit `21a526a`, and training it needs a GPU.
<!-- TODO(orcd): record how PIE's environment was built (/orcd/pool/005/rkern/immune_grn/external/pie_env). -->
