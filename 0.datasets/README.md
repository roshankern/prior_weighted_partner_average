# 0.datasets

This module downloads the Perturb-seq datasets and the priors, runs PIE's pipeline on the eight cell-level datasets, and splits the knocked-down genes into folds.
Downloads and processed data go to the data root (see [Data](../README.md#data)).
Git keeps only the tables in this folder and `splits/`.

| Notebook | What it does |
|---|---|
| [`0.download_perturbseq.ipynb`](0.download_perturbseq.ipynb) | Download every dataset in [`datasets.tsv`](datasets.tsv): cell-level counts, Marson's pseudobulk counts, and PIE's processed Replogle–Nadig arrays |
| [`1.download_priors.ipynb`](1.download_priors.ipynb) | Download the priors: PIE's five genetic knowledge sources |
| [`2.process_perturbseq.ipynb`](2.process_perturbseq.ipynb) | Run PIE's pipeline on the eight cell-level datasets, and build Marson's pseudobulk responses |
| [`3.split_genes.ipynb`](3.split_genes.ipynb) | Put each knocked-down gene in one of five folds, the same fold in every context; fold 4 is held out until the end |

## Datasets

| Dataset | Context | Species | Used in |
|---|---|---|---|
| Replogle et al. 2022 | K562 leukaemia line | human | [`2.train_test`](../2.train_test/) |
| Replogle et al. 2022 | RPE1 retinal epithelial line | human | [`2.train_test`](../2.train_test/) |
| Nadig et al. 2025 | HepG2 liver cancer line | human | [`2.train_test`](../2.train_test/) |
| Nadig et al. 2025 | Jurkat T-cell line, resting | human | [`2.train_test`](../2.train_test/) |
| Nourreddine et al. 2026 | KOLF2.1J iPSC | human | [`2.train_test`](../2.train_test/) |
| Roohani et al. 2025 (Virtual Cell Challenge) | H1 hESC | human | [`2.train_test`](../2.train_test/) |
| Shi et al. 2026 | mouse brain in vivo, 3 neuron types | mouse | [`2.train_test`](../2.train_test/) |
| Geiger-Schuller et al. 2026 | mouse dendritic cells, LPS-stimulated | mouse | [`2.train_test`](../2.train_test/) |
| Verma et al. 2026 (PIE) | PIE's processed Replogle–Nadig arrays | human | [`2.train_test`](../2.train_test/) |
| Zhu et al. 2026 | primary CD4+ T cells at rest, 8 h and 48 h after stimulation | human | [`3.further_analysis`](../3.further_analysis/) |
