# Essential gene check

**Model:** iML1515 (1516 genes) · **Medium:** rich-broth approximation (the app's aerobic glucose medium plus 36 nutrients LB supplies: amino acids, nucleosides and vitamins) · **Lethal below:** 1% of wild-type growth · **Wild-type growth:** 1.427 h⁻¹

**Ground truth:** PRECISE-1K — Lamoureux et al., "A multi-scale expression and regulation knowledge base for Escherichia coli", Nucleic Acids Research 51(19):10176 (2023), doi:10.1093/nar/gkad750; data from github.com/SBRG/precise1k at commit 4829b83, `essential` column (measured in rich medium).

## Result

Of the 1,514 genes in both the model and the lab data, the model calls **105** essential; the lab says **121**.

| Measure | Value | What it means |
| --- | --- | --- |
| Precision | 0.800 | Of the genes the model calls essential, the share the lab agrees are essential |
| Recall | 0.694 | Of the lab's essential genes, the share the model catches |
| F1 | 0.743 | Balance of precision and recall |
| MCC | 0.725 | Matthews correlation, −1 to 1; 0 is no better than chance. The fairest single number here, because essential genes are a small minority |
| Accuracy | 0.962 | Shown for completeness only — calling every gene non-essential would already score about 0.92 |

| | Lab: essential | Lab: not essential |
| --- | --- | --- |
| **Model: essential** | 84 (true positive) | 21 (false positive) |
| **Model: not essential** | 37 (false negative) | 1372 (true negative) |

## Coverage — what this model can speak to

The lab lists **300** essential genes; **121** of them are in the model. Most of the rest work outside metabolism (DNA replication, transcription, translation, cell division), which a metabolic model does not represent — so it cannot predict them either way. 2 model gene(s) have no lab record and are left out of the scoring.

## Do the setup choices matter?

Two choices could have steered the result: the lethality cut-off, and how much of each LB nutrient the cell may take up. The screen is re-scored and re-run with other values; if the scores held only for one value, that value would be suspect.

**Lethality cut-off** (same screen, re-scored):

| Lethal below | TP | FP | FN | Precision | Recall | F1 | MCC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1% | 84 | 21 | 37 | 0.800 | 0.694 | 0.743 | 0.725 |
| 5% | 84 | 21 | 37 | 0.800 | 0.694 | 0.743 | 0.725 |
| 10% | 84 | 21 | 37 | 0.800 | 0.694 | 0.743 | 0.725 |
| 25% | 84 | 21 | 37 | 0.800 | 0.694 | 0.743 | 0.725 |

**Nutrient uptake** (screen re-run; mmol/gDW/h per nutrient):

| Uptake | Wild-type growth (h⁻¹) | TP | FP | FN | F1 | MCC |
| --- | --- | --- | --- | --- | --- | --- |
| 1 (used) | 1.43 | 84 | 21 | 37 | 0.743 | 0.725 |
| 2 | 1.66 | 84 | 21 | 37 | 0.743 | 0.725 |
| 5 | 2.37 | 84 | 21 | 37 | 0.743 | 0.725 |

## Where the model disagrees with the lab

**False negatives — the lab says essential, the model says the cell survives (37).** Usually the model has an alternative route the real cell cannot use (the enzyme is absent, too slow or regulated off), or the gene matters for something besides its metabolic reaction.

| Gene | Locus | Product | Knockout growth (% of wild type) |
| --- | --- | --- | --- |
| acpS | b2563 | holo-[acyl-carrier-protein] synthase | 100.0% |
| adk | b0474 | adenylate kinase | 99.9% |
| alsK | b4084 | D-allose kinase | 100.0% |
| can | b0126 | carbonic anhydrase 2 | 100.0% |
| cydA | b0733 | cytochrome bd-I ubiquinol oxidase subunit I | 100.0% |
| cydC | b0886 | glutathione/L-cysteine ABC exporter subunit CydC | 100.0% |
| dut | b3640 | deoxyuridine triphosphatase | 100.0% |
| eno | b2779 | enolase | 77.3% |
| entD | b0583 | phosphopantetheinyl transferase EntD | 100.0% |
| fabA | b0954 | beta-hydroxyacyl-acyl carrier protein dehydratase/isomerase | 100.0% |
| fabB | b2323 | beta-ketoacyl-[acyl carrier protein] synthase I | 100.0% |
| fabI | b1288 | enoyl-[acyl-carrier-protein] reductase | 100.0% |
| fabZ | b0180 | 3-hydroxy-acyl-[acyl-carrier-protein] dehydratase | 100.0% |
| fbaA | b2925 | fructose-bisphosphate aldolase class II | 100.0% |
| fldA | b0684 | flavodoxin 1 | 100.0% |
| folA | b0048 | dihydrofolate reductase | 100.0% |
| folD | b0529 | bifunctional 5,10-methylene-tetrahydrofolate dehydrogenase/ 5,10-methylene-tetrahydrofolate cyclohydrolase | 100.0% |
| gapA | b1779 | glyceraldehyde-3-phosphate dehydrogenase A | 68.7% |
| gpsA | b3608 | glycerol-3-phosphate dehydrogenase | 99.8% |
| hemH | b0475 | ferrochelatase | 100.0% |
| ligA | b2411 | DNA ligase | 100.0% |
| lnt | b0657 | apolipoprotein N-acyltransferase | 100.0% |
| nrdA | b2234 | ribonucleoside-diphosphate reductase 1 subunit alpha | 100.0% |
| nrdB | b2235 | ribonucleoside-diphosphate reductase 1 subunit beta | 100.0% |
| pgk | b2926 | phosphoglycerate kinase | 68.7% |
| pgsA | b1912 | phosphatidylglycerophosphate synthase | 100.0% |
| plsB | b4041 | glycerol-3-phosphate 1-O-acyltransferase | 100.0% |
| ppa | b4226 | inorganic pyrophosphatase | 100.0% |
| prs | b1207 | ribose-phosphate diphosphokinase | 100.0% |
| purB | b1131 | adenylosuccinate lyase | 100.0% |
| pyrG | b2780 | CTP synthetase | 100.0% |
| pyrH | b0171 | UMP kinase | 100.0% |
| spoT | b3650 | bifunctional (p)ppGpp synthase/hydrolase SpoT | 100.0% |
| suhB | b2533 | inositol-phosphate phosphatase | 100.0% |
| tnaB | b3709 | tryptophan:H(+) symporter TnaB | 100.0% |
| waaU | b3623 | putative ADP-heptose:LPS heptosyltransferase 4 | 100.0% |
| wzyE | b3793 | enterobacterial common antigen polymerase | 100.0% |

**False positives — the model says lethal, the lab says the cell survives (21).** Usually the real cell has a backup the model lacks (an unannotated isozyme or salvage pathway), or LB provides a nutrient this medium approximation leaves out.

| Gene | Locus | Product | Knockout growth (% of wild type) |
| --- | --- | --- | --- |
| aroA | b0908 | 3-phosphoshikimate 1-carboxyvinyltransferase | 0.0% |
| aroB | b3389 | 3-dehydroquinate synthase | 0.0% |
| aroC | b2329 | chorismate synthase | 0.0% |
| aroD | b1693 | 3-dehydroquinate dehydratase | 0.0% |
| coaA | b3974 | pantothenate kinase | 0.0% |
| coaE | b0103 | dephospho-CoA kinase | 0.0% |
| cysG | b3368 | siroheme synthase | 0.0% |
| dapF | b3809 | diaminopimelate epimerase | 0.0% |
| folB | b3058 | dihydroneopterin aldolase | 0.0% |
| folP | b3177 | dihydropteroate synthase | 0.0% |
| glmM | b3176 | phosphoglucosamine mutase | 0.0% |
| hemE | b3997 | uroporphyrinogen decarboxylase | 0.0% |
| kdsC | b3198 | 3-deoxy-D-manno-octulosonate 8-phosphate phosphatase KdsC | 0.0% |
| lptB | b3201 | lipopolysaccharide transport system ATP binding protein | 0.0% |
| luxS | b2687 | S-ribosylhomocysteine lyase | 0.0% |
| metF | b3941 | 5,10-methylenetetrahydrofolate reductase | 0.0% |
| mtn | b0159 | 5'-methylthioadenosine/S-adenosylhomocysteine nucleosidase | 0.0% |
| pabA | b3360 | aminodeoxychorismate synthase subunit 2 | 0.0% |
| pabB | b1812 | aminodeoxychorismate synthase subunit 1 | 0.0% |
| yrbG | b3196 | putative transport protein YrbG | 0.0% |
| zupT | b3040 | heavy metal divalent cation transporter ZupT | 0.0% |

---
Generated by `python -m validation.essentiality` in 15 s. Per-gene results: `essentiality_genes.csv`.
