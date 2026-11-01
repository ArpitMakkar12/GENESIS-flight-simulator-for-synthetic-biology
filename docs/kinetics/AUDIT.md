# BRENDA audit trail (1 November 2026)

Every *E. coli* entry seen for each EC number, and why it was kept or dropped. Four batches, one section each.

---

## Batch A raw audit trail (BRENDA, accessed 2026-11-01)

Source pages: `https://www.brenda-enzymes.org/enzyme.php?ecno=<EC>&organism_list=Escherichia+coli`; references resolved via `literature.php?e=<EC>&r=<ID>`.
Rows with no mutant label in BRENDA are treated as wild-type (stated per EC where it matters).
Temperature filter for kcat: 25-37 C or not stated.

---

## 2.7.1.2 glucokinase (substrate D-glucose)

- TURNOVER NUMBER: section absent for E. coli.
- TEMPERATURE OPTIMUM: absent.
- pH OPTIMUM: absent.
- Page complete (fetched twice; ends with references and footer). Only KM rows exist: ATP 0.5 (641064), ATP 3.76 pH 7.65 (641065), D-glucose 0.15 (641064), D-glucose 0.78 pH 7.65 (641065). Not used.
- Result: all three empty.

## 5.3.1.9 glucose-6-phosphate isomerase (substrate D-glucose 6-phosphate)

- TURNOVER NUMBER / TEMPERATURE OPTIMUM / pH OPTIMUM: all absent for E. coli.
- Page complete (fetched twice). KM rows only: F6P 0.147 22 C pH 7.4 (661902); G6P 0.28 22 C pH 7.4 (661902); F6P 0.2 "enzyme forms PGI I and PGI II" (2841). Not used.
- Result: all three empty.

## 2.7.1.11 6-phosphofructokinase (substrate D-fructose 6-phosphate)

Enzyme page text was 74,632 characters and was cut off in the pH RANGE section, so TEMPERATURE OPTIMUM was not on it. Re-fetch with offsets confirmed the cut. The temperature table was read from `https://www.brenda-enzymes.org/all_enzymes.php?ecno=2.7.1.11&table=Temperature_Optimum` (BRENDA single-table view).

### kcat (25 E. coli rows)

| value | substrate | commentary | ref | decision |
|---|---|---|---|---|
| 0.25 | sedoheptulose 7-phosphate | pH 7.0, 55 C | 761519 | drop: alternative substrate |
| add. info | - | kcat increases with pH, GDP increases kcat | 640489 | drop: no number |
| 0.037 | ATP | wild type, Mn2+, pH 8.2, temp not specified | 721420 | drop: ATP is not the listed substrate (also Mn2+) |
| 0.24 | ATP | mutant E190Q, Mg2+ | 721420 | drop: mutant |
| 9 | ATP | mutant E190Q, Mn2+ | 721420 | drop: mutant |
| 62 | ATP | wild type, Mg2+, pH 8.2, temp not specified | 721420 | drop: ATP is not the listed substrate |
| 0.016 | D-F6P | pH 7.2, 30 C, cosubstrate gamma-thio-ATP | 640526 | drop: analogue co-substrate |
| 1.2 | D-F6P | pH 7.0, 55 C | 761519 | drop: 55 C |
| 44 | D-F6P | 0.5 mM MgATP2-, pH 8.2, 25 C (PFK-2) | 722736 | KEEP |
| 60 | D-F6P | 0.1 mM MgATP2-, pH 8.2, 25 C (PFK-2) | 722736 | KEEP |
| 0.015 | F6P | pH 8.0, 8.5 C, T125A mutant | 640517 | drop: mutant, temp |
| 0.3 | F6P | pH 8.5, 30 C, R72H mutant | 640490 | drop: mutant |
| 0.303 | F6P | pH 8.0, 8.5 C, R72E mutant | 640517 | drop: mutant, temp |
| 3.47 | F6P | pH 8.0, 8.5 C, R171E mutant | 640517 | drop: mutant, temp |
| 3.7 | F6P | pH 8.5, 30 C, R252Q mutant | 640519 | drop: mutant |
| 5 | F6P | pH 8.2, 5 C | 640491 | drop: 5 C |
| 49 | F6P | pH 7.2, 30 C, cosubstrate ATP | 640526 | KEEP (no mutant label; paper also studies M169A/M169L/R25S mutants) |
| 57.2 | F6P | pH 8.5, 30 C, I126A mutant | 640490 | drop: mutant |
| 60 | F6P | pH 8.2, 15 C | 640491 | drop: 15 C |
| 61 | F6P | pH 8.0, 8.5 C, wild-type | 640517 | drop: 8.5 C |
| 88 | F6P | pH 7.2, 30 C, at 2 mM ATP | 640526 | KEEP |
| 110 | F6P | pH 8.2, 25 C | 640491 | KEEP |
| 111 | F6P | pH 8.5, 30 C, wild-type | 640490 | KEEP |
| 167 | F6P | pH 8.5, 30 C | 640519 | KEEP (no mutant label) |
| 185 | F6P | pH 8.2, 37 C | 640491 | KEEP |

Kept: 44, 49, 60, 88, 110, 111, 167, 185 -> n=8, median 99 (mean of 88 and 110), min 44, max 185.
Isoenzymes pooled: PFK-2 (722736, Cabrera 2011, "phosphofructokinase-2 of E. coli") with PFK-1 (640526, 640490, 640519); 640491 (Kruger 1989) does not name the isoform.

### Temperature optimum

| value | commentary | ref | decision |
|---|---|---|---|
| add. info | effects of temperature on kinetic properties | 640491 | drop: no number |
| 27-28 | "assay at" | 640463 | KEEP, midpoint 27.5 (PFK2; commentary means it is the assay temperature, not a measured optimum) |

### pH optimum

| value | commentary | ref | decision |
|---|---|---|---|
| 6.2 | R72H mutant, strong decrease in activity above | 640519 | drop: mutant |
| 6.5 | isoenzyme PFK2, pH optima at 6.5 and 8.5 | 640463 | KEEP |
| 8.5 | isoenzyme PFK2, pH optima at 6.5 and 8.5 | 640463 | KEEP |
| 9-10.5 | - | 640519 | KEEP, midpoint 9.75 (no mutant label) |
| add. info | - | 640421 | drop: no number |
| add. info | pH-dependence of kinetic properties | 640490 | drop: no number |

Median of 6.5, 8.5, 9.75 = 8.5. No direction stated.

### References
- 722736: Cabrera R, et al. 2011, J Biol Chem 286:5774, PMID 21147773 (PFK-2)
- 640526: Wang X, Kemp RG 2001, Biochemistry 40:3938, PMID 11300773 (PFK-1)
- 640491: Kruger NJ 1989, Biochem Soc Trans 17:760, no PubMed ID on BRENDA
- 640490: Zheng RL, Kemp RG 1992, J Biol Chem 267:23640, PMID 1429704 (PFK-1)
- 640519: Zheng RL, Kemp RG 1995, Biochem Biophys Res Commun 214:765, PMID 7575542 (PFK-1)
- 640463: Kotlarz D, Buc H 1982, Methods Enzymol 90:60, PMID 6218375 (PFK1 and PFK2)

## 4.1.2.13 fructose-bisphosphate aldolase (substrate D-fructose 1,6-bisphosphate)

First fetch failed with a server error; the retry succeeded. The page was cut off only in the final Organism Search table, after all the needed sections.

### kcat (19 E. coli rows, all D-fructose 1,6-bisphosphate, all 30 C)

| value | commentary | ref | decision |
|---|---|---|---|
| 0.001 | N286D mutant | 652787 | drop |
| 0.0028 | D109A mutant | 652787 | drop |
| 0.013 | E174A mutant | 652876 | drop |
| 0.033 | E182A mutant | 652876 | drop |
| 0.16 | N35A mutant | 651064 | drop |
| 0.19 | N286A mutant | 652787 | drop |
| 0.58 | K325A mutant | 651064 | drop |
| 0.85 | S61A mutant | 651064 | drop |
| 2 | D144A mutant | 652787 | drop |
| 2.2 | D288A mutant | 652787 | drop |
| 5.8 | E181A mutant | 652876 | drop |
| 6.08 | K325A mutant | 651064 | drop |
| 6.3 | S61T mutant | 651064 | drop |
| 7 | D290A mutant | 652787 | drop |
| 8.2 | wild-type, P0AB71 | 652787 | KEEP |
| 8.5 | Q59A mutant | 651064 | drop |
| 10.5 | wild-type | 652876, 651064 | KEEP (one row, two refs) |
| 12.3 | D329A mutant | 652787 | drop |
| 14.2 | 30 C, P0AB71, no form label | 666802 | KEEP mechanically. The paper is a directed-evolution thermostable-variant study, and BRENDA's literature page does not tie 14.2 to wild-type or variant. |

Kept: 8.2, 10.5, 14.2 -> n=3, median 10.5, min 8.2, max 14.2. Without 14.2 the median would be 9.35.
Isoenzymes: every titled paper is about class II (FbaA, P0AB71). 651064 does not state its class, but its wild-type value shares a row with 652876 (class II). No class I (FbaB) data was seen, so nothing was pooled.

### Temperature optimum
- 57, no commentary, 746639 -> KEEP.

### pH optimum
- 9, no commentary, 4913 -> KEEP (Baldwin 1978, native class II enzyme from the Crookes strain).

### References
- 652787: Plater AR, et al. 1999, J Mol Biol 285:843, PMID 9878448
- 652876: Zgiby S, et al. 2002, J Mol Biol 315:131, PMID 11779234
- 651064: Zgiby SM, et al. 2000, Eur J Biochem 267:1858, PMID 10712619
- 666802: Hao J, Berry A 2004, Protein Eng Des Sel 17:689, PMID 15531627
- 746639: Zhang L, et al. 2014, Acta Crystallogr F 70:1376, PMID 25286943
- 4913: Baldwin SA, et al. 1978, Biochem J 169:633, PMID 417719 (strain: Crookes)

## 5.3.1.1 triose-phosphate isomerase (substrate D-glyceraldehyde 3-phosphate)

### kcat (1 E. coli row)
- 9000, D-glyceraldehyde 3-phosphate, "pH 7.6, wild-type enzyme", no temperature, 2586 -> KEEP (no temperature stated, so allowed).
- There is no DHAP-direction E. coli row. The GAP direction was chosen because it is the only one with E. coli wild-type data.
- Note: ref 2586 is a paper on the TIM of the psychrophile Vibrio marinus, in which E. coli TIM serves as the comparator.

### Temperature optimum
- Absent. Empty.

### pH optimum
- 8, "optimum is near pH 8.0", P0A858, 714686 -> KEEP. The ref is a review, and the entry has no wild-type/mutant label. The first literature fetch hit a server error; the retry succeeded.

### References
- 2586: Alvarez M, et al. 1998, J Biol Chem 273:2199, PMID 9442062
- 714686: Wierenga RK, et al. 2010, Cell Mol Life Sci 67:3961, PMID 20694739

## 1.2.1.12 glyceraldehyde-3-phosphate dehydrogenase (phosphorylating) (substrate D-glyceraldehyde 3-phosphate)

The page was cut off in MOLECULAR WEIGHT, after the needed sections. A second, focused fetch confirmed the turnover section.

### kcat
- 2 rows, both "additional information" with no numeric value, ref 287927 (one row P0A9B2) -> drop: no number. No kcat/KM section.
- Result: empty.

### Temperature optimum
- 55, no commentary, P0A9B2, 762579 -> KEEP. This is recombinant His-tagged GapA. The source gives no wild-type/mutant label.

### pH optimum
| value | commentary | ref | decision |
|---|---|---|---|
| 10 | - | 762579 | KEEP |
| 8 | 50 mM Tris-chloride and triethanolamine-chloride buffer | 287977 | KEEP |
| 8.8 | 50 mM sodium diphosphate buffer | 287977 | KEEP |

Median 8.8. No entry states a reaction direction. The first literature fetch for 287977 hit a server error; the retry succeeded.

### References
- 762579: Zhang L, et al. 2020, Acta Crystallogr F 76:406, PMID 32880588
- 287977: D'Alessio G, Josse J 1971, J Biol Chem 246:4326, PMID 4326214

## 2.7.2.3 phosphoglycerate kinase (substrate 1,3-bisphosphoglycerate, or 3-phosphoglycerate for the reverse direction)

### kcat
- The E. coli page has no TURNOVER NUMBER section, so there is no data for either direction. The all_enzymes.php turnover table view showed no E. coli rows either, but that view is abbreviated with collapsed groups, so it is not conclusive on its own.

### Temperature optimum
- 23, "assay at", 642260 -> KEEP mechanically. The commentary means this is the assay temperature, not a measured optimum.

### pH optimum
- 7.5, "assay at", 642260 -> KEEP mechanically, with the same caveat. No direction is stated.

### References
- 642260: D'Alessio G, Josse J 1975, Methods Enzymol 42C:139, no PubMed ID on BRENDA

## 5.4.2.11 phosphoglycerate mutase (2,3-diphosphoglycerate-dependent) (substrate 3-phosphoglycerate)

- The first fetch failed with a server error; the retry succeeded.
- TURNOVER NUMBER / TEMPERATURE OPTIMUM / pH OPTIMUM: all absent on the E. coli page, which is complete. The all_enzymes.php turnover table view lists only S. cerevisiae, S. pombe and L. lactis.
- Result: all three empty.

## 5.4.2.12 phosphoglycerate mutase (2,3-diphosphoglycerate-independent) (substrate 3-phosphoglycerate)

- No functional-parameter sections on the E. coli page (count 0). The page is complete.
- Result: all three empty.

---

## Batch B: raw BRENDA entries and audit trail

Source: BRENDA, accessed 1 Nov 2026 with WebFetch. Only *Escherichia coli* rows are listed.

**How the pages were read.** `enzyme.php?ecno=<EC>&organism_list=Escherichia+coli` loaded completely only for 1.1.1.42, 4.2.1.11, 1.2.4.2 and 2.7.1.40. For 1.3.5.1 the page text ended in the Cofactor section (75,510 characters; data loads dynamically). For 2.3.3.1 it rendered with every count at 0. For 4.2.1.3, 4.2.1.2 and 6.2.1.5 the server returned errors. In those cases, and to cross-check, I read the BRENDA per-table pages `all_enzymes.php?ecno=<EC>&table=Turnover_Number|pH_Optimum|Temperature_Optimum` and asked for the E. coli rows, including rows inside collapsed groups. References were resolved through `literature.php?e=<EC>&r=<ID>`.

**Global decision (please review).** BRENDA puts "assay at" in the commentary when the value in a pH- or temperature-optimum field is only the assay condition, not a measured optimum. I **excluded all "assay at" entries** from T-opt and pH-opt. Every excluded value is listed below so the decision can be reversed. It changes these results:
- **T-opt** becomes empty for 2.7.1.40, 1.3.5.1, 4.2.1.2 and 6.2.1.5.
- **pH-opt** becomes empty for 2.7.1.40, 1.1.1.42 and 6.2.1.5.

Legend: **KEPT** means used in the CSV value. **DROP** means not used, with the reason given.

---

## 4.2.1.11: phosphopyruvate hydratase (enolase), matches the expected enzyme
- **kcat:** No E. coli rows in the Turnover Number table. The table has 13 rows in all, from *S. cerevisiae*, *P. falciparum*, *K. pneumoniae*, *H. sapiens* and *T. annulata*. The enzyme.php page also has no Turnover section. Result: kcat empty.
- **T-opt:** No E. coli rows (the table covers 19 organisms). Result: empty.
- **pH-opt:**
  - 8.1, no commentary, refs 33600 and 33605. **KEPT**. Result: **8.1**.
- **Refs:**
  - 33600 = Spring and Wold, *J. Biol. Chem.* 1971, PMID 4942326
  - 33605 = Spring and Wold, *Methods Enzymol.* 42C, 1975, no PMID on BRENDA

## 2.7.1.40: pyruvate kinase, matches the expected enzyme
- **kcat:** No E. coli rows. I checked all 38 rows of the phosphoenolpyruvate group; they come from 11 other organisms. The enzyme.php page also has no Turnover section. So there are no PykF or PykA values to pool. Result: kcat empty.
- **T-opt:**
  - 25, "assay at", ref 641557. **DROP** (assay at).
  - 30, "assay at", ref 723111. **DROP** (assay at).
  - 37, "assay at", UniProt P0AD62 and A0A0H3JER5, ref 721624. **DROP** (assay at).
  - Result: empty.
- **pH-opt:**
  - 7.2, "assay at", ref 723111. **DROP** (assay at).
  - 7.5, "assay at", ref 721624. **DROP** (assay at).
  - Result: empty.

## 2.3.3.1: citrate (Si)-synthase, **no E. coli data under this EC**
- **enzyme.php (filtered to E. coli):** Every functional count is 0 and the reference count is 0. Only PDB links (1NXE, 1OWB, 1OWC, 1NXG) mention E. coli.
- **all_enzymes Turnover_Number:** 18 rows, all from *C. merolae*, *H. sapiens* and *S. scrofa*.
- **CSV result:** kcat, T-opt and pH-opt are all empty.
- **Supplementary, not entered in the CSV:** BRENDA files E. coli GltA under **EC 2.3.3.16, "citrate synthase (unknown stereospecificity)"**. Turnover rows found there:
  - **Oxaloacetate:**
    - 81, wild-type, +0.1 M KCl, ref 659254. Would be kept.
    - 92, wild-type, pH 7.8, 25 °C, ref 756709. Would be kept.
    - 56, 89 and 114: K295, K168 and K283 acetylated variants, ref 756709. Dropped (not wild-type).
    - 3–6, 54, 67, 84, 95, 108, 118, 121, 124: mutants Y145A, T111A, H110A, K167A, Q182A, R163L, T204A, R109L, N189A, ref 659254. Dropped (mutants).
    - Result: median 86.5, n=2.
  - **Acetyl-CoA, wild-type (not needed because oxaloacetate values exist):**
    - 34, pH 8.0, 37 °C, ref 762840
    - 34, pH 8.0, 37 °C, ref 778426
    - 44, no conditions given, ref 735698
    - 81, +0.1 M KCl, ref 488069
    - 81, +0.1 M KCl, ref 659254
    - The mutants A267T, F383M, T204R, G181E and the 659254 set were dropped.
  - **pH-opt:** 7.8, "recombinant chimeric protein", ref 488069. Dropped (not wild-type).
  - **T-opt:** No E. coli rows visible. Some groups were collapsed and could not be checked.
  - **Refs:**
    - 659254 = Stokell 2003, PMID 12824188
    - 756709 = Venkat 2019, PMID 30974512

## 4.2.1.3: aconitate hydratase, matches the expected enzyme
- **kcat:** Two E. coli rows, both "additional information" with no number: ref 488175 (one with UniProt P36683, one without). The citrate (9), isocitrate (9) and cis-aconitate (3) groups were listed in full and contain no E. coli. **DROP** (no numeric value). Result: kcat empty.
- **T-opt:** No E. coli rows. Result: empty.
- **pH-opt:**
  - 7.5, "enzyme form AcnA and AcnB, the maximal activity of AcnB is nearly 2fold the activity of AcnA", ref 649675. **KEPT** (covers both AcnA and AcnB).
  - 8, UniProt P36683, "assay at", ref 696416. **DROP** (assay at).
  - Result: **7.5**.
- **Refs:** 649675 = Jordan 1999, *Biochem. J.* 344:739, no PMID on BRENDA.

## 1.1.1.42: isocitrate dehydrogenase (NADP+), matches the expected enzyme
This page loaded completely: 12 turnover rows, 2 T-opt rows and 1 pH-opt row.
- **kcat:**
  - 51.8, isocitrate, wild-type, pH 7.5, 25 °C, ref 761403. **KEPT**.
  - 106.4, isocitrate, 40 °C, pH 8.0, ref 722205. **DROP** (above 37 °C).
  - 0.18 and 0.3, isocitrate, mutants R153H and R153C, ref 761403. **DROP** (mutants).
  - 1 and 1, 2-oxoglutarate, mutants, ref 761403. **DROP** (mutants and wrong substrate).
  - 88.1, NADP+, 40 °C, ref 722205. **DROP** (cofactor, not the substrate).
  - "additional information" rows, ref 722205. **DROP** (no number).
  - Result: **51.8**, n=1.
- **T-opt:**
  - 50, UniProt P08200, no commentary, ref 722205. **KEPT**.
  - 40, "assay at", ref 722205. **DROP** (assay at).
  - Result: **50**.
- **pH-opt:**
  - 8, "assay at", ref 722205. **DROP** (assay at).
  - Result: empty.
- **Refs:**
  - 761403 = Song 2017, PMID 27406240
  - 722205 = Stokke 2007, PMID 17401542. This paper is about IDH chimeras of *Archaeoglobus fulgidus* and *E. coli*.

## 1.2.4.2: oxoglutarate dehydrogenase (succinyl-transferring), matches the expected enzyme
All 20 turnover rows come from ref 762591, with no strain given. I confirmed with an offset read that the page has no pH-opt or T-opt sections (Specific Activity is followed directly by Organism).
- **kcat:**
  - 2.7, 2-oxoglutarate, wild-type, pH 8.0, 30 °C. **KEPT**.
  - 35, 2-oxoglutarate, wild-type, pH and temperature not specified. **KEPT**.
  - 2-oxoglutarate mutants. **DROP** (mutants):
    - 0.73 (H298D)
    - 6.8 (E1o-H298D/E2o-H348Y)
    - 7.3 (H348F)
    - 8.4 (S333M)
    - 10.5 (H348Q)
    - 21.1 (E1o-H298D)
  - 2-oxo-5-hexenoate (0.0595 wild-type; 0.148, 0.65, 0.86, 0.99, 1.68 mutants). **DROP** (analogue substrate).
  - 2-oxovalerate (0.152 wild-type; 0.34, 0.38, 0.48, 0.57, 0.81 mutants). **DROP** (analogue substrate).
  - Result: **median 18.85**, n=2. The two kept values differ 13-fold.
- **T-opt and pH-opt:** No data.
- **Refs:** 762591 = Chakraborty 2020, *AIChE J.*, no PMID on BRENDA.

## 6.2.1.5: succinate-CoA ligase (ADP-forming), matches the expected enzyme
I checked the substrate groups: the only succinyl-CoA row is from *Acetobacter aceti* (201, pH 8.0, 25 °C; ref not captured). **There is no E. coli value in the physiological succinyl-CoA direction**, so I used the succinate direction.
- **kcat:**
  - 14.3, succinate, E. coli K-12, P0AGE9 and P0A836, recombinant, pH 7.4, 30 °C, ref 726747. **KEPT**.
  - 44.73, succinate, "wild type enzyme, apparent value", ref 671076. **KEPT**.
  - 0.3, 15.3, 29.25, 31 and 35.38, succinate, mutants C123αA, V, S, T and A, ref 671076. **DROP** (mutants).
  - 0.2 (3-sulfinopropionate), 1.2 (D-malate), 1.5 (itaconate), 1.8 (L-malate), ref 726747. **DROP** (analogue substrates).
  - ATP 19.6, CoA 26.7, ref 726747. **DROP** (co-substrates, not the forward substrate).
  - ATP and GTP mutant rows (0.21–2343), ref 650157, mutants E197β and E208α at 22 °C. **DROP** (mutants). The values of about 1775–2343 for mutants look anomalous.
  - "additional information", ref 823. **DROP** (no number).
  - Result: **median 29.515**, n=2.
- **T-opt:**
  - 30, K-12, "assay at", ref 726747. **DROP** (assay at).
  - Result: empty.
- **pH-opt:**
  - 7.4, K-12, "assay at", ref 726747. **DROP** (assay at).
  - Result: empty.
- **Refs:**
  - 726747 = Nolte 2014, PMID 24141127
  - 671076 = Hidber 2007, PMID 17642514

## 1.3.5.1: succinate dehydrogenase, matches the expected enzyme, **but many entries are fumarate reductase**
- **Where the data came from:** The enzyme.php page was truncated, so the values come from the all_enzymes tables. The E. coli turnover set has 93 rows.
- **The problem:** Several "wild-type succinate" rows come from fumarate reductase (FrdABCD) papers. Ref titles show this for 674634, 674532 and 391172; rows from 674532 and 654820 carry UniProt P00363. BRENDA's own comment on ref 654820 names EC 1.3.5.4 for the menaquinone reaction.
- **My decision:** I excluded Frd as a different enzyme. This goes beyond the literal protocol, so the figures with Frd included are given too.
- **kcat (substrate succinate):**
  - 80, 30 °C, pH 7.8, no mutant flag, ref 656003. **KEPT**. This is the SQR/complex II paper; the same ref has an 82 row with phenazine ethosulfate as acceptor, so the acceptor for the 80 is possibly PES.
  - 167–217, no conditions, ref 391145 (SQR purification). **KEPT** as the midpoint, 192.
  - 167–217, ref 391172 (Dickie 1979, "membrane-bound fumarate reductase"). **DROP** (Frd).
  - 20.4, wild-type, menaquinone, pH 7.9, 30 °C, ref 674634 (Frd). **DROP** (Frd).
  - 28.3, wild-type, ubiquinone, pH 7.9, 30 °C, ref 674634 (Frd). **DROP** (Frd).
  - 66.7, wild-type, pH 7.0, 30 °C, P00363, ref 674532 (Frd). **DROP** (Frd).
  - 15 and 90–100, "fumarate reduction", P00363, ref 654820. **DROP** (direction contradicts the substrate; also Frd).
  - Mutants: 0.3 and 0.3 (K228R/L), 0.4 (E49L), 2.4 (E49F), 3.16 and 10 (E49A), 23 (E49F), 24 (E49L). **DROP** (mutants).
  - Other substrates (fumarate, menaquinol, ubiquinone, ferricyanide, MTT tetrazolium, reduced plumbagin, 2,3-dimethoxy-5-methyl-1,4-benzoquinone (DMMB), phenazine ethosulfate (PES)). **DROP** (not the forward substrate). These include wild-type rows such as 29.6 (MTT, ref 685281), 28.9 (ferricyanide, ref 742846), 32.2 (ubiquinone, ref 742846), 222.2 and 0.2 (menaquinol, ref 742846), 250 and 2.8 (fumarate, refs 674634 and 674532), and 182 (DMMB, ref 391104).
  - "additional information" rows (654820: succinate oxidation with menaquinone 3.4 s⁻¹; fumarate reduction with ubiquinone 28 s⁻¹; 391137). **DROP** (no structured value).
  - **Result (SDH only):** median **136**, n=2, range 80–192.
  - **With Frd pooled in** (20.4, 28.3, 66.7, 80, 192, 192): median 73.35, n=6.
- **pH-opt:**
  - 7.4–7.8, "for both succinate dehydrogenase and fumarate reductase", ref 391137. **KEPT** as 7.6.
  - 8, no commentary, ref 685281 (SDH). **KEPT**.
  - 6.6–6.8, no commentary, ref 391091 (Lemire 1986, "Fumarate reductase of E. coli"). **DROP** (Frd). Including it gives 7.6.
  - 6.6–6.8 "assay at" (ref 391169), 7.4 "assay at" (ref 698668), 7.8 "assay at" (P00363, ref 654820), 8 "assay at" (ref 696480). **DROP** (assay at).
  - Result: **7.8**.
- **T-opt:**
  - 38 "assay at" (ref 391104), 25 "assay at" (refs 685281 and 698668), 30 "assay at" (refs 696480 and 654820), 30 "assay at" (P00363, ref 654820). **DROP** (assay at).
  - Result: empty.
- **Refs:**
  - 656003 = Maklashina 2001, PMID 11259408
  - 391145 = Tornroth 2002, PMID 11803025
  - 391137 = Maklashina 1999, PMID 10486141
  - 685281 = Cheng 2008, PMID 18690748
  - Checked but dropped:
    - 674634 = Maklashina 2006, PMID 16829675 (Frd)
    - 674532 = Maklashina 2006, PMID 16484232 (Frd/SQR homologs)
    - 391172 = Dickie 1979, PMID 383238 (Frd)
    - 391091 = Lemire 1986, PMID 3078445 (Frd)

## 4.2.1.2: fumarate hydratase, matches the expected enzyme
- **kcat:**
  - 51.7, fumarate, "fumarase A", ref 33771. **KEPT** (FumA).
  - 1149, fumarate, P05042, pH 7.9, native enzyme, ref 653794. **KEPT** (FumC).
  - 1150, fumarate, P05042, pH 7.9, native enzyme, ref 653794. **KEPT** (FumC). This may duplicate the 1149 row.
  - 11.2, (S)-malate, fumarase A, ref 33771. **DROP** (reverse direction).
  - 1, L-malate, mutant E315Q, ref 653794. **DROP** (mutant, reverse).
  - "additional information" rows, refs 33770 and 33771. **DROP** (no number).
  - There is no FumB value.
  - Result: **median 1149**, n=3, pooled.
- **pH-opt:**
  - 8, "enzyme form FUMC", ref 33768. **KEPT**.
  - 8.5, "enzyme form FUMA", ref 33768. **KEPT**.
  - 6.9 "assay at" ×3 (E. coli; K-12, P14407; O157:H7), ref 749072. **DROP** (assay at).
  - 8 "assay at", ref 730721. **DROP** (assay at).
  - Result: **8.25**. Including "assay at" entries would give 7.45.
- **T-opt:**
  - 37 "assay at" (refs 730721, 749072, and 749072 for O157:H7). **DROP** (assay at).
  - 0.09437, K-12, P14407, "assay at", ref 749072. **DROP** (assay at; the value is evidently a BRENDA data error).
  - Result: empty.
- **Refs:**
  - 33771 = Flint 1994, PMID 8203917
  - 653794 = Estevez 2002, PMID 12021453
  - 33768 = Ueda 1991, PMID 1917897

---

## Batch C raw audit trail (BRENDA, accessed 2026-11-01)

Access method: the full `enzyme.php?ecno=<EC>&organism_list=Escherichia+coli` page was cut off by the fetcher for large entries (e.g. 2.3.1.54 ends inside KM VALUE at ~75k chars), so the per-table view `&onlyTable=Turnover_Number | Temperature_Optimum | pH_Optimum | Reference` was used on the same URL. A table that comes back with only the "Please wait a moment until all data is loaded" notice was checked against the unfiltered table for 4.1.1.49: that table had no E. coli rows, so this notice means BRENDA has no E. coli rows. References were resolved from `onlyTable=Reference` or `literature.php?e=<EC>&r=<ID>`.

Legend: KEEP = used, DROP = excluded (reason given).

---
## 1.1.1.37 — (S)-malate dehydrogenase (NAD+, oxaloacetate-forming); expected substrate L-malate
kcat (all E. coli rows; no L-malate/(S)-malate rows exist):
- 0.77, oxaloacetate, pH 7.5 30C, recombinant mutant R81Q, [689763]. DROP: mutant, and reverse-direction substrate
- 931, oxaloacetate, pH 7.5 30C, recombinant wild-type, [689763]. DROP: not the natural forward substrate (OAA, reverse direction)
- Result: no E. coli wild-type kcat
T-opt:
- 30, "assay at", [689763]. KEEP
pH-opt:
- 6, mutant N122C-L305C, [286668]. DROP: mutant
- 7.5, "assay at", [689763]. KEEP (direction not stated)
Refs: 689763 = Yin 2007, PMID 17947381 (E. coli MG1655; MDH-to-LDH paralog-shift mutants)

## 1.1.1.49 — glucose-6-phosphate dehydrogenase (NADP+); expected substrate D-glucose 6-phosphate
The first full-page fetch failed with a server error. The Turnover_Number table view worked.
kcat (10 E. coli rows; each lists the cofactor as substrate, none lists D-glucose 6-phosphate):
- 109 NAD+ K18A pH 8.2 25C [741254]; 165 NAD+ K18A/R50A [741254]; 171 NAD+ R50A [741254]. DROP: mutant
- 288 NAD+ 25C pH 8.0 [722244]; 288 NAD+ wild-type pH 8.2 25C [741254]. DROP: substrate is NAD+ (non-natural cofactor), not G6P
- 143 NADP+ K18A [741254]; 185 NADP+ K18A/R50A [741254]; 189 NADP+ R50A [741254]. DROP: mutant
- 174 NADP+ 25C pH 8.0 [722244]; 174 NADP+ wild-type pH 8.2 25C [741254]. DROP: substrate column is NADP+, not D-glucose 6-phosphate (reported in notes as a candidate)
- Result: no E. coli wild-type kcat
T-opt:
- 25, "assay at", [722244, 722473]. KEEP (counted once per ref)
- 28, "assay at", [722580]. KEEP. Median 25
pH-opt:
- 7.5 "assay at" [722580]; 8 "assay at" [722244]; 8 [722473]; 8 "assay at" [722577]. All KEEP. Median 8
Refs: 722244 Olavarria 2012 PMID 22519976; 722473 Banerjee 1972 PMID 4401601 (wild-type and "high-level" mutant strain); 722580 Cavalieri 1973 PMID 4348919; 722577 Sanwal 1970 PMID 4392411; 741254 Fuentealba 2016 PMID 27010804 (not used)

## 1.2.4.1 — pyruvate dehydrogenase (acetyl-transferring); expected substrate pyruvate
kcat (17 E. coli rows):
- E2p lipoyl domain, pH 7.0 30C [725205]: 0.08 H407A, 0.7 D549A, 0.83 E401K, 3.31 Y177A. DROP: mutant. 95 wild-type. DROP: substrate is the E2p lipoyl domain, not pyruvate
- pyruvate with 2,6-dichlorophenolindophenol (DCPIP), 30C [687613]: 0.081 H407A, 0.21 K403E, 0.39 E401K, 1.53 K410E, 3.07 N404A, 3.64 E401A, 4.41 K403A, 7.68 K410A, 19.03 Q408A, 25.12 K411E, 35.13 K411A. DROP: mutant
- 37.9, pyruvate, wild-type, DCPIP, 30C [687613]. DROP: measured with an artificial electron acceptor (analogue co-substrate)
- Result: no E. coli wild-type kcat
T-opt (the first try at the table view failed with a server error; the retry worked):
- "additional information", commentary "value for pyruvate dehydrogenase complex: 45C", [348960]. KEEP as 45. This is the only E. coli entry, and it is for the complex.
pH-opt:
- 6.5-7.5, no commentary, [348960]. KEEP, midpoint 7.0
Refs: 348960 Saumweber 1981 PMID 7011811 (E. coli K12 PDH E1 component)

## 1.1.1.28 — D-lactate dehydrogenase; expected substrate pyruvate (to D-lactate)
kcat (E. coli rows, all [739841], recombinant, 30C, wild-type/mutant not stated):
- 31 2-oxobutyrate pH 7.0; 100 glyoxylate pH 7.0; 50 hydroxypyruvate pH 7.0; 1100 oxaloacetate pH 7.0. DROP: alternative substrates
- 640 / 690 (+Mg2+) / 710 / 730 (+FBP) NADH, pH 7.0 / 8.0. DROP: substrate is the cofactor NADH, not pyruvate
- 370 pyruvate pH 8.0 +Mg2+. KEEP
- 380 pyruvate pH 8.0. KEEP
- 400 pyruvate pH 8.0 +fructose 1,6-bisphosphate. KEEP
- 410 pyruvate pH 7.0. KEEP
- Median 390, n=4, all from ref 739841
T-opt:
- 30, "assay at", [739841]. KEEP
pH-opt:
- 6.4-7.5 [286430]. KEEP (6.95)
- 7-8 "assay at" [739841]. KEEP (7.5)
- 7.5 "assay at" [684633]. KEEP. Median 7.5
Refs: 739841 Furukawa 2014 PMID 25401076; 286430 Garvie 1980 PMID 6997721; 684633 Okino 2008 PMID 18188553 (D-lactate production in C. glutamicum)

## 2.3.1.54 — formate C-acetyltransferase (= pyruvate formate-lyase); expected substrate pyruvate
The full page was cut off inside KM VALUE. The table views were used.
kcat (7 E. coli rows; none mentions mutant or wild-type):
- 105 CoA pH 8.5 21C [767140]; 225 CoA pH 8.1 20C [777926]. DROP: substrate CoA (reverse/co-substrate)
- 3.8 formate [487220]; 4.33 formate "backward direction" [487231]. DROP: reverse direction
- 11 pyruvate, no conditions [487220]. KEEP
- 12.8 pyruvate "forward direction" [487231]. KEEP (no temperature stated)
- 225 pyruvate pH 8.1 20C [777926]. DROP: below 25C
- Median 11.9, n=2
T-opt:
- 30 "assay at" [672694]; 30 "assay at" [744943] (P09373). KEEP. Median 30
pH-opt:
- 7.6 "assay at" [672694]. KEEP
- 7.8-8.4 [487221]. KEEP (8.1)
- 7.8-8.5 "forward direction" [487220]. KEEP (8.15)
- 8.5 "assay at" [671620]. KEEP. Median 8.125
Refs: 487220 Knappe 1974 PMID 4615902; 487231 Himo 1998 (no PMID; theoretical study of PFL mechanism); 672694 Yang 2007 PMID 17341838; 744943 Zhang 2015 PMID 25979691 (PFL pathway in S. cerevisiae); 487221 Knappe 1975 (no PMID); 671620 Nnyepi 2007 PMID 17280641

## 4.1.1.49 — phosphoenolpyruvate carboxykinase (ATP); expected substrate oxaloacetate (to PEP)
The first full-page fetch showed TURNOVER NUMBER, but T-opt and pH-opt were not in the captured text. The table views show no E. coli rows for either.
kcat (E. coli):
- 0.67 phosphoenolpyruvate pH 7.0 37C [727382]. DROP: reverse direction
- OAA pH 7.5 25C [769275] mutants: 0.0005 R333Q, 0.012 K212S, 0.025 R65Q, 0.025 K254S, 0.028 D269N, 0.03 H232Q, 0.035 K213S, 0.3 S250A. DROP: mutant
- 0.433 OAA wild-type pH 7.5 25C [769275]. KEEP. n=1
T-opt: no E. coli rows. The unfiltered table has only Oryza sativa [682374] and S. cerevisiae [682700, 678490]. Result: no data
pH-opt: no E. coli rows. The unfiltered table has 20 entries from 8 other organisms. Result: no data
Refs: 769275 Sokaribo 2020 PMID 31911238 (E. coli K12)

## 3.1.3.11 — fructose-bisphosphatase; expected substrate D-fructose 1,6-bisphosphate (Fbp + GlpX pooled)
kcat (16 E. coli rows):
- 2.5, fructose 1,6-bisphosphate, wild-type, no conditions [693243] (GlpX). KEEP
- 5.7, pH 9.0 37C, wild-type [693243] (GlpX). KEEP
- 1.1 E59A, 1.2 D186A, 5.4 R235A, 7.5 K239A, 14 K29A, pH 9.0 37C [693243]. DROP: mutant
- 11.3 L54A 22C [665621]. DROP: mutant
- 8, 22C pH 7.5, Mg2+-initiated [680756] (P0A993). DROP: 22C
- 20, wild-type 22C pH 7.5 [665621]. DROP: 22C
- 24, 22C pH 7.5 [680756]; 26, 22C +1 mM PEP [680756]. DROP: 22C
- 14.6, pH 7.5 30C [650375] (Fbp). KEEP
- 22, pH 7.5, no temperature [652492]. KEEP (protein not named in the title; assumed Fbp)
- 2 "additional information" rows without values [651666]. DROP: no value
- Median 10.15, n=4, min 2.5, max 22
T-opt:
- 37 "assay at" [693243] (GlpX). KEEP
pH-opt:
- 7.8 [650375]. KEEP
- 7.5 [170730]. KEEP
- 7.5, commentary "pH optimum: 7.5-8.0" [693243]. KEEP as 7.5 (value field). Using the 7.75 midpoint would make the median 7.75
- "additional information" (activity ratio pH 7.5/9.5) [665621]. DROP: no value
- The page showed a collapsed "7.5 (2 entries)" group, which matches the two 7.5 rows above. Median 7.5
Refs: 693243 Brown 2009 PMID 19073594 (GlpX type II); 650375 Kelley-Loughnane 2002 PMID 11825604; 652492 Choe 2003 PMID 14530289; 170730 Babul 1983 PMID 6312898; 680756 Hines 2007 PMID 17314096 (not used); 665621 Iancu 2005 PMID 15767255 (not used)

## 1.1.1.1 — alcohol dehydrogenase; expected substrate acetaldehyde (AdhE)
- The TURNOVER NUMBER, TEMPERATURE OPTIMUM and pH OPTIMUM tables have no E. coli rows: the table views return only the loading notice, and the full E. coli page (which reached the footer, so it was not cut off) has none of these sections.
- E. coli data on this EC: the organism is listed with refs 660650 and 763497; the reaction ethanol + NAD+ = acetaldehyde + NADH; KM ethanol 10.6 mM [660650]; Ki 4-methylpyrazole 18.26 mM [660650]. The refs were not resolved, so which Adh protein this is was not identified.
- Result: kcat, T-opt and pH-opt all empty

## 2.7.2.1 — acetate kinase; expected substrate acetyl phosphate (direction used: acetyl phosphate + ADP -> acetate + ATP)
The Turnover_Number table view failed with a server error. The full E. coli page worked and showed the complete table.
kcat (all E. coli, P0A6A3):
- acetyl phosphate pH 7.5 recombinant [739591]: 890 (10C), 1550 (15C), 2150 (20C). DROP: below 25C. 3600 (25C). KEEP
- ADP pH 7.5 [739591]: 892/1565/2178/3515 (10-25C). DROP: co-substrate, same experiment
- acetate pH 7.5 [739591]: 560/760/1165/1420 (10-25C). DROP: other direction
- ATP: 565/745/1130/1500 (10-25C) [739591]; 908 wild-type pH 6.5 30C [738717]. DROP: other direction. ATP mutants 0.34, 9.9, 10.5, 16.3, 41, 395 [738717]. DROP: mutant
- Result: 3600, n=1
T-opt:
- 30 "assay at" [738717]; 37 "assay at" [738863]; 70 "about" [739591]. All KEEP. Median 37. The only real optimum given is about 70C.
pH-opt:
- 6.5-7.5, "acetyl phosphate-forming reaction direction, assay at" [738717]. DROP: opposite of the direction used
- 6.4 [642167]. KEEP
- 7.5 [642166, 642182]. KEEP
- 7.5 "assay at" [738863, 739591]. KEEP
- 7.5 "assay at" [739591]. KEEP. Median 7.5
Refs: 739591 Tang 2014 PMID 24801996 (psychrophilic vs mesophilic AckA); 738717 Yoshioka 2014 PMID 24856051; 738863 Zhang 2015 PMID 26370798 (whole-cell dTTP production); 642167 Anthony 1971 PMID 4942557; 642166 Rose 1962 (book chapter, no PMID); 642182 Fox 1986 PMID 3020034

---

## Batch D raw audit trail (BRENDA, accessed 2026-11-01)

Pages: `enzyme.php?ecno=<EC>&organism_list=Escherichia+coli`. Where that page failed with a server error (2.6.1.1, 7.1.1.2) or was truncated (7.1.2.2), the `all_enzymes.php?ecno=<EC>&table=Turnover_Number | Temperature_Optimum | pH_Optimum` tables were used and filtered to E. coli. References were resolved with `literature.php?e=<EC>&r=<ID>`.
Entries with no wild-type/mutant label were treated as wild-type (non-mutant). K = kept, D = dropped.

## 2.3.1.8 phosphate acetyltransferase (substrate acetyl-CoA)
Cross-checked on enzyme.php and all_enzymes.php (10 E. coli turnover rows on both).

kcat [1/s]
| val | substrate | commentary | ref | K/D | reason |
|---|---|---|---|---|---|
| 0.15, 1.56, 2.16 | acetyl phosphate | mutant Pta-F1, pH 8.0, 30C | 719451 | D | mutant and reverse substrate |
| 227 | acetyl phosphate | wild-type, pH 8.0, 30C (P0A9M8) | 719451 | D | reverse-direction substrate |
| 415 | acetyl phosphate | pH 7.8, 30C | 720217 | D | reverse-direction substrate |
| 0.03, 0.23, 0.43 | acetyl-CoA | mutant Pta-F1, pH 8.0, 30C | 719451 | D | mutant |
| 29.6 | acetyl-CoA | wild-type, pH 8.0, 30C (P0A9M8) | 719451 | K | Pta |
| 120 | acetyl-CoA | pH 7.8, 30C | 720217 | K | EutD isoenzyme (Bologna 2010, "E. coli EutD: a phosphotransacetylase of the ethanolamine operon"), pooled |
Median 74.8 (n=2).

T-opt: 37, "activity assay", 705531 (K; flagged as probable assay condition).
pH-opt: 7.8, "activity assay", 705531 (K; same flag).

Refs: 719451 Campos-Bermudez 2010 FEBS J PMID 20236319; 720217 Bologna 2010 J Microbiol PMID 21046341; 705531 Castano-Cerezo 2009 Microb Cell Fact PMID 19852855.

## 2.6.1.1 aspartate transaminase (substrate L-aspartate)
enzyme.php failed twice (server error). The all_enzymes.php Turnover_Number table had 72 rows, 24 of them E. coli.

kcat [1/s]
| val | substrate | commentary | ref | K/D | reason |
|---|---|---|---|---|---|
| additional information | - | mutants | 639884 | D | no value / mutants |
| 1.44 / 2.69 | 2-methoxyphenylpyruvate | WT / mutant, pH 8, 40C | 759006 | D | analogue; 40C |
| 1.81 / 4.33 | 3,4-dimethoxyphenylpyruvate | WT / mutant, 40C | 759006 | D | analogue |
| 1.55 / 2.79 | 3-methoxyphenylpyruvate | WT / mutant, 40C | 759006 | D | analogue |
| 1.77 / 2.85 | 4-methoxyphenylpyruvate | WT / mutant, 40C | 759006 | D | analogue |
| 2.99 / 3.45 | phenylpyruvate | WT / mutant, 40C | 759006 | D | analogue |
| 0.35 / 0.38 | 2-oxo-4-phenylbutanoate | WT / mutant R292E/L18H | 658335 | D | analogue |
| 0.305 / 5.55 | L-Lys | WT / mutant | 658335 | D | analogue |
| 43 | L-Asp | pH 8, multi-mutant A12T/... | 658035 | D | mutant |
| 10 | L-Phe | same mutant | 658035 | D | mutant, analogue |
| 0.13 | L-aspartate | pH 7.5, 25C, mutant I33Q/Y214Q/R280Y | 721734 | D | mutant |
| 0.03 | L-glutamate | mutant | 721734 | D | mutant, reverse |
| 670 | L-glutamate | pH 7.5, 25C, wild-type | 721734 | D | reverse-direction substrate |
| 40.64 | L-cysteine | pH 7.4, 30C | 759136 | D | alternative substrate |
| 259 | L-aspartate | wild-type, pH 8.4, 25C | 639884 | K | |
| 530 | L-aspartate | pH 7.5, 25C, wild-type (P00509) | 721734 | K | |
| 24.43 | L-aspartate | pH 7.4, 30C (P00509) | 759136 | K | unlabeled; recombinant aspC expressed in BL21(DE3) |
Median 259 (n=3, 24.43 to 530).

T-opt
| val | commentary | ref | K/D |
|---|---|---|---|
| 35 | - (P00509) | 759136 | K |
| 25 | assay at | 639823 | K (assay condition) |
| 25 | assay at (P00509) | 639879, 721734 | K (assay condition; one row, two refs) |
Median 25. Without the "assay at" rows it would be 35.

pH-opt
| val | commentary | ref | K/D | reason |
|---|---|---|---|---|
| 7.4 | assay at (D3H0F7) | 721617 | K | |
| 7.5 | assay at (P00509) | 721734 | K | |
| 7.5-8.5 -> 8.0 | - | 639815, 639855 | K | range midpoint |
| 8 | assay at (P00509) | 639879 | K | |
| 8 | formation of aspartate | 636643 | D | reverse direction |
| 8.5 | substrates L-Phe or L-Trp | 636643 | D | alternative substrates |
| 9 | substrate L-Tyr | 636643 | D | alternative substrate |
Median 7.75. The pH table had collapsed groups, so hidden E. coli rows cannot be fully excluded.

Refs: 639884 Deu 2002 Protein Sci PMID 11967363; 721734 Fernandez 2012 BBA PMID 22138634; 759136 Andreessen 2017 Enzyme Microb Technol PMID 28193330; 639823 Kamitori 1987 J Biochem PMID 3298223; 639879 Birolo 1999 Biochemistry PMID 9893985; 721617 Liu 2010 Biochemistry PMID 21033689; 639815 Yagi 1985 Methods Enzymol PMID 3003515; 639855 Yagi 1979 FEBS Lett PMID 374118 (E. coli B).

## 2.6.1.2 alanine transaminase (substrate L-alanine)
enzyme.php (E. coli filter) shows Functional Parameters = 0 entries. The all_enzymes.php Turnover_Number, Temperature_Optimum and pH_Optimum tables have no E. coli rows; the organisms listed are P. putida, Zea mays, Rattus, yeasts and others.
E. coli entries exist only in the cofactor, crystallization and cloning sections: AlaA, UniProt P0A959, ref 739493 (Pena-Soler 2014 PLoS ONE PMID 25014014; crystal structure of AlaA compared with AlaC and AvtA).
Kept: nothing. Conclusion: this is the correct EC for E. coli AlaA, but BRENDA has no E. coli kinetics.

## 2.6.1.11 acetylornithine transaminase (substrate N2-acetyl-L-ornithine)
Recommended name: acetylornithine transaminase. Systematic name: N2-acetyl-L-ornithine:2-oxoglutarate 5-aminotransferase. Reaction: N2-acetyl-L-ornithine + 2-oxoglutarate = N-acetyl-L-glutamate 5-semialdehyde + L-glutamate. E. coli genes named: ArgD, AstC, GabT, PuuE (ref 739103). This is NOT alanine aminotransferase.
kcat: no E. coli rows. The only rows are Salmonella Typhimurium (0.82 L-ornithine; 1.55 N2-acetyl-L-ornithine; ref 689939), dropped as wrong organism.
T-opt: 37 "assay at", refs 644946 and 644947 (K; assay condition).
pH-opt: 8 (644947) K; 8.1 (644946) K. Median 8.05.
Refs: 644946 Albrecht 1964 J Biol Chem PMID 14213368; 644947 Billheimer 1976 J Bacteriol PMID 8431.

## 7.1.1.2 NADH:ubiquinone reductase (H+-translocating) (substrate NADH)
enzyme.php failed twice (server error). Data came from the all_enzymes.php tables.

kcat [1/s]
| val | substrate | commentary | ref | K/D | reason |
|---|---|---|---|---|---|
| 1500 | hexaammineruthenium(III) chloride | - | 672041 | D | analogue acceptor |
| 2-8 | NADH | mutant E183Q, pH 6, 30C | 725443 | D | mutant |
| 11 | NADH | mutant E183N | 725443 | D | mutant |
| 37 | NADH | mutants E183D, E183H | 725443 | D | mutant |
| 26 | NADH | wild-type, pH 6.0, 30C | 725443 | K | acceptor not stated (paper used ferricyanide and O2 assays) |
| 3 | NADPH | wild-type, pH 6, 30C | 725443 | D | alternative substrate |
| 10, 11, 14, 34 | NADPH | mutants | 725443 | D | mutant, alternative substrate |
kcat 26 (n=1).

T-opt: 30 "assay at", refs 725443 and 724310 (K). The table had collapsed groups (Sus scrofa, Bos taurus, Aquifex) that might hide rows.

pH-opt
| val | commentary | ref | K/D | reason |
|---|---|---|---|---|
| 7-8 -> 7.5 | - | 394359 | K | caution: ref is an FMN-dependent menadione-induced NADH-quinone reductase, not complex I |
| 6-7 | mutant E183H, NADH | 725443 | D | mutant |
| 6 | mutant E183H, NADPH | 725443 | D | mutant |
| 6 | wild-type, NADH, first peak | 725443 | K | |
| 6 | assay at | 724310 | K | |
| 6.5 | wild-type, NADPH | 725443 | D | alternative substrate |
| 7.5 | assay at | 725517 | K | |
| 7.5 | wild-type, NADH, second higher peak | 725443 | K | |
Median 7.5. Without 394359 the median is 6.75.

Refs: 725443 Morina 2011 J Biol Chem PMID 21832062; 724310 Steimle 2011 Biochemistry PMID 21417432; 394359 Hayashi 1990 BBA PMID 2118386; 725517 Narayanan 2013 J Biol Chem PMID 23543743.

## 7.1.1.3 ubiquinol oxidase (H+-transporting) (substrate ubiquinol)
Systematic name: quinol:oxygen oxidoreductase (H+-transporting). Synonyms include cytochrome bo3, Cyo oxidase, cyoABCD, cyoA-D. They also include cytochrome bd, bd-I, bd-II, CydA, CydB, CydX and CydAB, which is odd.

kcat [1/s] (cross-checked on enzyme.php and all_enzymes.php; 3 rows in total)
| val | substrate | commentary | ref | K/D | reason |
|---|---|---|---|---|---|
| additional information | ubiquinol-1 -> ubiquinone-1 (P26458) | turnover rate 63 e-/s, pH 7, temp n.s. | 767917 | D | no numeric value; analogue |
| 300 | ubiquinol-1 | 60 mM Tris-HCl pH 7.5, 25C | 714286 | D | analogue (Q1, not native Q8) |
| 341 | ubiquinol-1 | 60 mM Tris-HCl pH 7.5, 25C | 714286 | D | analogue |
If Q1 were accepted, the median would be 320.5. Ref 714286 is Bolgiano 1993 BBA PMID 8382081 (membrane-bound cytochrome bo, strains E. coli and E. coli RG145).
T-opt: no section. pH-opt: no section.

## 7.1.1.7 quinol oxidase (electrogenic, proton-motive force generating) (substrate ubiquinol)
Systematic name: quinol:oxygen oxidoreductase (electrogenic, non H+-transporting). Synonyms: cytochrome bd-I, bd quinol oxidase, CydA, CydB, CydAB, CydX. No bo3/Cyo synonyms.
kcat: 101, substrate H2O2[side 2], UniProt P0ABJ9; P0ABK2; P56100, pH 7.0, temp n.s., ref 752197. Dropped: this is the quinol peroxidase reaction (decylubiquinol + H2O2), not the natural substrate. It is the only E. coli row.
T-opt: no data.
pH-opt: 7, no commentary, ref 752197 (K; flagged because it comes from the peroxidase paper).
Ref: 752197 Al-Attar 2016 Sci Rep PMID 27279363 ("Cytochrome bd displays significant quinol peroxidase activity").

## 7.1.2.2 H+-transporting two-sector ATPase (substrate ATP; hydrolysis direction)
Reaction as written: ATP + H2O + 4 H+[side 1] = ADP + phosphate + 4 H+[side 2], which is the hydrolysis direction. enzyme.php was truncated, so I cross-checked with all_enzymes.php (16 rows in total, 6 of them E. coli).

kcat [1/s], all with "pH 7.5-8.8, temperature not specified in the publication", ref 712371
| val | substrate | variant | K/D | reason |
|---|---|---|---|---|
| 16 | ADP | recombinant wild-type F1Fo | D | synthesis-direction substrate |
| 55 | ADP | epsilon mutant | D | mutant |
| 285 | ATP | recombinant wild-type F1Fo | K | direction not labelled by BRENDA |
| 539 | ATP | epsilon mutant | D | mutant |
| 20 | phosphate | wild-type | D | synthesis-direction substrate |
| 66 | phosphate | epsilon mutant | D | mutant |
kcat 285 (n=1).

T-opt: no E. coli rows. The table might be incomplete: the page summary says 33 records but only about 23 were visible.

pH-opt
| val | commentary | ref | K/D | reason |
|---|---|---|---|---|
| 7.5-8.8 | ATP synthesis activity assay at | 712371 | D | reverse direction |
| 9-9.5 -> 9.25 | - | 210238 | K | |
| 7.5 | assay at | 711528 | K | direction not stated; whole-cell study with hydrogenase mutants |
| 7.5 | ATP hydrolysis activity assay at | 712371 | K | |
Median 7.5. Collapsed groups (6.5/7, 7.5, 8) might hide rows.

Refs: 712371 Iino 2009 J Biol Chem PMID 19411254; 210238 Abrams 1974 The Enzymes 3rd ed. vol 10 (book chapter, no PMID); 711528 Blbulyan 2010 Biosci Rep PMID 20662772.

## 2.7.1.1 hexokinase (substrate D-glucose)
The enzyme.php page with the E. coli filter shows 0 entries in every section and 0 references. E. coli is absent as both a source organism and an expression host.
Kept: nothing.
