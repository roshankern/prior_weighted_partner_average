# 4.experiment_log

The engineering of PWPA was assisted by an autonomous, LLM-driven lab loop.
These notes record what that loop tried and found. 
They are written mainly for future LLM agents that work on this repository or on similar problems.

This module has no code. Its numbers come from the lab's own code on the MIT ORCD cluster, not from this repository's notebooks (see [Caveats](#caveats)).

## How the experiments were run

- **The loop.**
  - A Claude session acted as principal investigator (the "PI agent"). It woke up on a schedule and read a charter written by the human researcher. It chose one experiment, wrote its plan, ran it as Slurm jobs, scored it and logged the result.
  - Subagents ran literature searches and side tasks.
  - The researcher steered each session by adding a section to the charter: a new goal, a new metric or a new rule. They also asked for some experiments directly, outside the loop: most of the K, L and R series.
- **The experiment contract.** Every experiment has a folder with a README in a fixed form:
  - a question and a hypothesis;
  - a prediction, written before any job ran;
  - the method, with one named comparator and a control;
  - the result.
- **Controls.**
  - perm0 shuffles gene identities in the priors.
  - Decoys are permuted copies of a source.
- **Findings and scores.** Durable conclusions went into a numbered findings log (#1–#200), each with its evidence and a confidence. Negative results are included.
- **Splits and bars.**
  - Knockdowns were split into 5 gene folds per dataset. Folds 0–3 are dev; fold 4 is the lockbox, scored rarely and only on request.
  - A claim needed +0.03 over its comparator (paired SE over test rows), and it also had to hold at a second panel size.
- **Scale.** About 580 experiment arms and controls ran over 9 loop sessions (2026-09-28 to 2026-10-06), and researcher-directed runs continued until mid-October 2026.

## How to use this log

1. Read [Lessons](#lessons) and [Ideas that failed](#ideas-that-failed) below.
2. Search [`experiments.tsv`](experiments.tsv) for your idea: one row per arm, with columns `id stage parent datasets metric split result comparator delta_se verdict takeaway`.
3. Open the stage file for the full setup and numbers. Each detailed entry gives the question, setup, prediction, result, verdict and the lesson for later work.
4. Before comparing any two numbers, check that they share a metric and a split (next section).

| File | Ids | When | Question |
|---|---|---|---|
| [`0.fixed_rules.md`](0.fixed_rules.md) | E000–E122 (315 arms) | Sessions 1–5, 2026-09-28 to 10-01 | Which fixed similarity rule over which sources beats STRING as a prior? Includes the session-5 metric fix |
| [`1.learned_scorers.md`](1.learned_scorers.md) | F001–F035, G001–G007 (71) | Sessions 6–7, 10-01 to 10-04 | Can a learned scorer over the sources beat the hand rules? Does it transfer to other T-cell data? |
| [`2.gated_model.md`](2.gated_model.md) | H001–H014, M001 (76) | Session 8, 10-04 to 10-05 | The simplest model as good as the learned one: one gate per dataset (PWPA's form), selection, and the GRN it implies |
| [`3.sources_and_datasets.md`](3.sources_and_datasets.md) | J001–J113 (32) | Session 9, 10-05 to 10-06 | Does the unchanged pipeline transfer to 10 Perturb-seq datasets, and do ~100 more sources help? |
| [`4.pie_benchmark_and_rfe.md`](4.pie_benchmark_and_rfe.md) | K001–K042, R031–R033, L005, L007 (21) | 10-07 to 10-14 | PWPA on PIE's benchmark with PIE's metrics; RFE replaces L1 + decoys as the selection |
| [`5.comparison_models.md`](5.comparison_models.md) | M010–M030, R001–R030, L001–L006, J020 (30) | Sessions 2–9 and after | GEARS, TxPert, scGPT and Fawkes (the STRING neighbour average), set up on the same splits |
| [`6.ood_llm_priors.md`](6.ood_llm_priors.md) | K050–K095 (37) | From 10-14 | Extension: priors built by LLMs for out-of-distribution data (Shi mouse brain first) |

## Metrics

The metric changed twice. Each entry names the metric and split behind its numbers.

- **Old Pearson Δ − k** (sessions 1–4). Δ is a knockdown's response, and k is the context's mean training response. The score is the Pearson correlation of predicted and true Δ − k, over each test row's own top-N DE genes. **It was biased:** predicting "k × 1.1" for every row scored 0.286, above STRING. About two thirds of the session-4 front's lead over STRING was this artifact.
- **Fixed panel** (from session 5). For each condition and fold, the panel is the 300 genes with the largest mean |z| over the training knockdowns, scored as Pearson Δ − k and as MSE in log2FC. b predicts k; it scores 0 on Pearson and is the MSE bar. r is the agreement between donor or cell halves. Later sessions scored normalised expression instead of z.
- **PIE's metrics** (K series). AUPRC, Jaccard, DE direction match, Spearman effect size, Spearman LFC and Discrimination L1, from PIE's code at FDR 0.05.

Many conclusions transferred across metrics, smaller. For example, measured-phenocopy priors led STRING by +0.091 on the old metric and +0.050 on the panel (E071a, dev). The PWPA form led Fawkes by +0.092 ± 0.014 on the expression lockbox. The stage files say where a result transferred, shrank or reversed.

## Lessons

Each lesson cites its stage file (by number) and experiment ids. Numbers are dev unless marked; "panel" is the fixed panel 300.

1. **Average the measured knockdowns that should behave alike: that is the whole model.**
   - Partner averaging beat network propagation and every learned head without it. Removing the attention ("memory") path from the learned hybrid cost −0.064 ± 0.004 (1: F013c, F025c).
   - Picking partners from the screen's own training responses failed, by −0.05 to −0.22 old (0: E002, E003, E019).
2. **Measured phenocopy priors carry the signal; knowledge priors barely add.**
   - DepMap co-essentiality is the core source (0, 1, 2).
   - Interaction networks, literature, embeddings, complexes, L1000, morphology and LLM partner lists each tied or lost to STRING, and added ≤ 0.003 on top of the measured kernels (0: E011–E076).
   - In session 9, ~90 knowledge, network, expression and embedding sources added at most about +0.02 where no sibling screen was kept (3).
3. **Other cell lines' Perturb-seq gives the large steps, inside one family of screens.**
   - On the session-9 pool, expanded − current was +0.104 ± 0.010 (RPE1), +0.067 (HepG2), +0.066 (K562) and +0.040 (Nadig Jurkat), panel. 54–71% of the gate weight sat on sibling screens.
   - It was under 0.03 or unreadable on Marson, Song, VCC H1, KOLF, Shi and Geiger (3: J011, J090).
   - On PIE's split the same family added only +0.020 on average, and AUPRC moved from 0.340 to 0.343 (4: K010, K011).
   - It is a soft leak by design: the screens share guide libraries and labs.
   - **The gain without any Perturb-seq source was never measured.**
4. **Pick genes for scoring and for training losses from training knockdowns only.**
   - The truth-picked gene sets of sessions 1–4 inflated every flexible model. F004 went from 0.396 old to 0.170 on the panel, below STRING. Size fits on those genes moved predictions 2–3× too far (0, 1: F004, E120).
   - Keep a "k × 1.1" control in any new metric.
5. **One non-negative gate per dataset is enough.**
   - The linear gated scorer with the plain T-cell channel (H004b, 9 numbers) tied the MLP pair scorer F034 on the lockbox: −0.004 ± 0.010 Pearson, +0.0003 ± 0.0007 MSE (2).
   - Dropping the per-condition sizes and the state mean cost −0.0004 ± 0.0003. That gave PWPA's form, H013-plain, refit on expression as H013x-expr-plain (2).
6. **Extra machinery bought under 0.01 each.** Per-row size heads, partner-strength terms, per-condition gates, coverage inputs, per-state fits and seed ensembles all added under 0.01 each (1, 2). With one size per condition, MSE skill ≈ (mean Pearson)², so size moves only through direction (1: #134). Averaging two different learned families did add +0.0085 ± 0.0032 (1: F023, F032).
7. **The gains are gene-specific.** Shuffled-identity (perm0) controls fall to b: panel 0.022 for the pick, against 0.297 (2: H004b-perm0). Learned scorers kept 0.06–0.09 from coverage patterns alone (1).
8. **Gate size is not contribution, and "kept" is not "useful".**
   - In drop-one refits, coess (gate 0.059) was worth +0.0003 ± 0.0027, while the T-cell channel (gate 0.031) was worth −0.011 (2: H012).
   - Shapley values ranked PIE's five sources differently from their gates (4: K034; 6: K054).
   - Datasets are largely redundant: the six single-dataset losses summed to 0.052, against a model score of 0.297.
9. **Selection: use RFE, but know its weakness.**
   - L1 with the 1-SE rule kept a decoy in 16 of 20 fits. The decoy-calibrated rule worked but was conservative (2: H003, H003b).
   - RFE (drop the smallest gate and refit) matched the decoy rule with fewer datasets. On K562 all 14 candidates scored 0.6147, and 7 datasets scored the same (4: R031, R032).
   - Because RFE ranks by gate size, adding PIE's five sources made small RFE sets worse, by −0.010 at 7 datasets. High-gate, low-coverage sources outlasted depmap and string (4: R033).
10. **Published deep models score below the zero-parameter neighbour average in this regime.**
    - On Marson and K562, GEARS, TxPert and scGPT all score below Fawkes (panel, expression). The best loses by −0.089 ± 0.010 (Marson) and −0.048 ± 0.007 (K562) (5).
    - Across ten datasets TxPert + STRING beats Fawkes only on HepG2 (5: J020).
    - These models trained on a few thousand pseudobulk samples, not on single cells. Read the setup notes before reusing the comparison.
11. **PWPA restricted to STRING is Fawkes, rescaled.** Pearson is identical row by row: 0.1653 against 0.1661 on Marson. Only MSE improves. PWPA's Pearson lead therefore comes from the other sources (5: L003).
12. **On PIE's benchmark, scoring choices matter as much as models.**
    - With exactly PIE's five gene sources, PWPA scored AUPRC 0.332 against PIE's published 0.304 (4: K031). The clean repo reruns this with RFE in [`2.train_test`](../2.train_test/).
    - A ranking by training DE frequency, the same for every test knockdown, scores 0.282. That is the honest AUPRC floor, not the context mean's 0.082.
    - Ranking the knocked-down gene itself as DE (the on-target "fill") lifts a no-information model to 0.409. Keep the fill off (4: K020).
13. **PIE wins on out-of-distribution data under its own pipeline.**
    - Over 8 datasets, PWPA had the higher AUPRC on the five cancer and stem-cell lines. PIE was higher on KOLF, Shi and Geiger (6: K061, K062).
    - Line priors for unseen cell contexts failed: 0.289–0.304 against PIE's 0.424 (4: K040–K042).
14. **The limit is the weights, not the form.**
    - On Marson, convex weights fitted to one donor half predict the other at 0.408, against r 0.397. In the same unit the pick scores 0.249 (2: H011).
    - On Shi, a prior built from held-out measured responses adds +0.137 ± 0.014, where every LLM prior adds about +0.01 (6: K076).
    - Better priors, not a different model, are the open lever.
15. **LLM-built priors: one simple form transfers, but under the bar.**
    - One call per gene scored, 0–4, how alike each other gene's knockout would look. It added +0.013 ± 0.003 on Shi, and +0.014 ± 0.004 pooled over Song, Geiger and KOLF (6: K086, K092).
    - Showing the LLM measured responses (retrieval) leaked or lost. A stronger model or more reasoning did not help (6: K078, K080, K082).
16. **Priors are worth several times the data.**
    - On 10% of training knockdowns, the kernel prior tied STRING given all of them (old metric; 0: E091).
    - PWPA's learning curve on Marson was still rising at 664 knockdowns per state (4: L005).

## Ideas that failed

Do not rerun these without a new reason. Each row gives the result and the stage file.

| Idea | Result | Where |
|---|---|---|
| Partners from the screen's own co-response, or "j moves i" | −0.14 and −0.22 vs STRING (old) | 0: E002, E003 |
| STRING channels, GenePT, PubTator3, HumanBase, Affinage, complexes, co-abundance, morphology, L1000 as priors | −0.003 to −0.147 vs STRING (old) | 0: E011–E069 |
| Blood-only co-essentiality; RNAi co-dependency; HAP1 genetic interactions | −0.077, −0.124, −0.051 (old) | 0: E016e, E046, E039 |
| Flexible response-basis model (F004) | 0.396 old → 0.170 panel, below STRING | 1: F004 |
| Learned per-source encoders; parametric head without memory | MSE above b; 0.245–0.257 vs 0.298 | 1: F008, F010 |
| Sparse attention | Raised the inner validation loss; learned attention is broad | 1: F018 |
| Per-state models, per-condition gates, coverage input, size heads | Under +0.01 each | 1, 2: F021, F030, F035, H002b, H006, H014 |
| L1 path with the 1-SE rule as the selector | Kept decoys | 2: H003 |
| Splitting T-cell screens by study or screen; whitening them | No change | 2: H004, H005, H004f |
| GO or GO + STRING inside GEARS / TxPert | No measurable change | 5: M012, M013, M022 |
| scGPT as a comparison model | At b; cannot represent most knockdowns | 5: M030, R020 |
| Learned line priors for unseen contexts; frozen gate transfer | No AUPRC gain over the equal average | 4: K040–K042 |
| LLM phenocopy lists, signatures, paragraph or claim embeddings, programs, stress sets | −0.004 to +0.008 each; best stack +0.012, not confirmed on the lockbox | 6: K051–K085 |
| LLM retrieval of measured responses (RAG), with or without abstention | −0.017 / +0.001; leaks when symmetrised | 6: K078, K080 |
| Stronger LLM or high reasoning effort for partners | No better precision; ~20× the cost | 6: K082 |
| In-context RL on LLM partner lists | Lost on test | 6: K089 |

## Caveats

- **Not reproducible from this repository.**
  - The numbers come from the lab's code, which lives in a private working tree on ORCD (`~/rotation_project/immune_grn/lab/exp/<id>/`). The paths are given for provenance.
  - This repository reprocesses the data with PIE's pipeline, uses PIE's metrics and selects with RFE, so its numbers differ.
- **Leaks and spent lockboxes.**
  - Sibling-screen Perturb-seq is a soft leak (lesson 3).
  - Marson's fold 4 was partly used during development, and Shi's lockbox is spent (6: K085).
- **Spreads.** Spreads on PIE's metrics are the sd over folds, except K034, which is SE. Everything else is a paired SE over test rows.
- **Sources disagree in places.** Each stage file lists where the findings log and an experiment README disagree, and which value it kept.
