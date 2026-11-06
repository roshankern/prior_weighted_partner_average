# 0.datasets

This module downloads the Perturb-seq datasets and the priors, runs PIE's pipeline on the eight cell-level datasets, and splits the knocked-down genes into folds.
Downloads and processed data go to the data root (see [Data](../README.md#data)).
Git keeps only the tables in this folder and `splits/`.

| Notebook | What it does |
|---|---|
| [`0.download_perturbseq.ipynb`](0.download_perturbseq.ipynb) | Download every dataset in [`datasets.tsv`](datasets.tsv): cell-level counts, Marson's pseudobulk counts, and PIE's processed Replogle–Nadig arrays |
| [`1.download_priors.ipynb`](1.download_priors.ipynb) | Download the priors: PIE's five genetic knowledge sources, and the two text sources only PIE uses |
| [`2.process_perturbseq.ipynb`](2.process_perturbseq.ipynb) | Run PIE's pipeline on the eight cell-level datasets, and build Marson's pseudobulk responses. Needs a GPU and PIE's `pie` command, and downloads the HGNC and MGI gene tables |
| [`3.split_genes.ipynb`](3.split_genes.ipynb) | Put each knocked-down gene in one of five folds, the same fold in every context; fold 4 is held out until the end |

`splits/<dataset>.tsv` lists each dataset's kept knockdowns, one row per context and knockdown, with its fold and its part (train, validation, test or lockbox) in each development fold.
The knockdowns were chosen on the cluster before any fold was drawn: TxPert's knockdown sets for Replogle and Nadig, and Marson's rule (more than 75 DE genes and more than 50 cells) for the others.
[`2.process_perturbseq.ipynb`](2.process_perturbseq.ipynb) reads them to pick the cells, and [`3.split_genes.ipynb`](3.split_genes.ipynb) redraws the folds and splits from them.

## Datasets

| Dataset | Context | Notes |
|---|---|---|
| Replogle et al. 2022 | Human K562 leukaemia line | PWPA against PIE in [`2.train_test`](../2.train_test/) |
| Replogle et al. 2022 | Human RPE1 retinal epithelial line | PWPA against PIE in [`2.train_test`](../2.train_test/) |
| Nadig et al. 2025 | Human HepG2 liver cancer line | PWPA against PIE in [`2.train_test`](../2.train_test/) |
| Nadig et al. 2025 | Human Jurkat T-cell line, resting | PWPA against PIE in [`2.train_test`](../2.train_test/) |
| Nourreddine et al. 2026 | Human KOLF2.1J iPSC | PWPA against PIE in [`2.train_test`](../2.train_test/); each knockdown was screened in one of three batches |
| Roohani et al. 2025 (Virtual Cell Challenge) | Human H1 hESC | PWPA against PIE in [`2.train_test`](../2.train_test/); the challenge's training, validation and test files together |
| Shi et al. 2026 | Mouse brain in vivo, 3 neuron types | PWPA against PIE in [`2.train_test`](../2.train_test/); 74 mice; genes named by their human orthologue to match the priors |
| Geiger-Schuller et al. 2026 | Mouse dendritic cells, LPS-stimulated | PWPA against PIE in [`2.train_test`](../2.train_test/); 16 hashtagged samples over 2 rounds; genes named by their human orthologue |
| Verma et al. 2026 (PIE) | Human K562, RPE1, HepG2 and Jurkat | PIE's processed arrays and published splits, for PIE's own benchmark in [`2.train_test`](../2.train_test/) |
| Zhu et al. 2026 | Human primary CD4+ T cells at rest, 8 h and 48 h after stimulation | Pseudobulk counts only, for [`3.further_analysis`](../3.further_analysis/); not scored against PIE, whose pipeline needs cell-level counts |
