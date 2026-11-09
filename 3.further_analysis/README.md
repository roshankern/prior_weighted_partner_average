# 3.further_analysis

These analyses extend the main comparison and use the Marson CD4+ T cell screen (Zhu et al. 2026), in which knockdowns were measured at rest and 8 h and 48 h after stimulation.
Here PWPA starts from ten priors: PIE's five genetic knowledge sources and five genome-wide CRISPR screens in primary human T cells (Carnevale 2022, Shifrut 2018 and Schmidt 2022 from BioGRID ORCS, Chen 2025 and Liu 2026 from the papers' tables).
A screen gives each gene one score, and two genes are alike when losing either pushes the screen's phenotype the same way; [`1.model/0.build_priors.ipynb`](../1.model/0.build_priors.ipynb) builds them and only this section uses them.
RFE keeps seven: DepMap, STRING, the perturbation description, ESM2, and the Chen (FOXP3 induction), Liu (abundance in tumours) and Schmidt (IL-2 production) screens.

| Notebook | What it does |
|---|---|
| [`0.partner_contributions.ipynb`](0.partner_contributions.ipynb) | Split a prediction into its partners and each partner's score into priors |
| [`1.gene_regulatory_network.ipynb`](1.gene_regulatory_network.ipynb) | Predict every screened gene to get a regulator by target network per cell state |

## Partners and priors

![Top partners of LCK](figures/partners_lck.png)

Every prediction comes with its partners, their weights, and how much each prior adds to each partner's score.
A partner's score does not depend on the cell state, but LCK's set of partners does: each state has its own knocked-down genes.
At rest the weight is spread thin: 503 partners share it, and the top five hold 22%.
ZAP70, which LCK activates at the T-cell receptor, leads with 13.5%, followed by ZAP70's sister kinase SYK and by CSK, which switches LCK off.
48 hours after stimulation the receptor's own chains, CD3D, CD3E and CD247 (CD3ζ), which LCK phosphorylates, and VAV1, which passes the signal on, join ZAP70 at the top; they were knocked down only after stimulation.
The weight is then more concentrated: 266 partners, 38% on the top five.
Most of each top partner's score comes from STRING and, for the receptor genes, from the Schmidt IL-2 screen, where losing them changes IL-2 production the way losing LCK does.

## Gene regulatory network

![From the trained model to a network](figures/grn_export.png)

Predicting every gene turns the model into a network: one row per regulator, one column per target gene, one table per cell state.
On Marson that is 11,526 regulators, every gene the screen targeted, by 10,273 targets, in three states.

![Regulator similarity across states](figures/grn_states.png)

The network changes with cell state the way the biology does.
Each square compares the rows of two known regulators, on a log scale shared by the three states.
Mediator–SAGA genes, general transcription machinery, have similar rows in every state.
T-cell activation genes are barely alike at rest, strongly alike at 8 hours, the strongest pairs in the figure, and still alike at 48 hours.
At 8 hours the two groups also move together as the whole cell responds to stimulation, and by 48 hours they have separated again.

These are two regulator clusters from Zhu et al. (Figure 3), and the predicted network reproduces what they found in the measured knockdowns: Mediator–SAGA members have correlated effects in all three states, and the T-cell activation cluster is active mainly after stimulation.
The network extends their map to every gene the screen targeted, including those whose knockdown failed, by predicting each gene's effect from its partners in each state.
An entry is the total predicted effect of a knockdown, not direct regulation, and the row of a gene that was never knocked down is only as good as its partners.
