# Enzyme kinetics: what was curated and why the engine does not use it

## What was done (1 November 2026)

The 32 kinetic entries in the old `seed_brenda.py` had no references, and every temperature optimum was 37 °C. They were re-curated from BRENDA for 36 EC numbers (the 32 plus four checks of suspected wrong EC numbers) with a fixed rule, written in `PROTOCOL.md`. Every value seen is listed in `AUDIT.md` with its BRENDA reference ID and the reason it was kept or dropped.

| File | Contents |
| --- | --- |
| `PROTOCOL.md` | The selection rule, plus the amendments made after the first pass |
| `AUDIT.md` | Every *E. coli* entry seen, kept or dropped, with reasons |
| `all_36_ec_numbers.csv` | All 36 EC numbers: old value, BRENDA value, Davidi et al. 2016 value, references |
| `../../backend/app/data/kinetics_curated.csv` | The 18 rows with a BRENDA *E. coli* kcat; what `seed_brenda.py` loads |

## What was found

- **Coverage:** BRENDA has a usable wild-type *E. coli* kcat for 18 of the 32 enzymes. Glucokinase, phosphoglucose isomerase, GAPDH, phosphoglycerate kinase, both phosphoglycerate mutases, enolase, pyruvate kinase, aconitase, malate dehydrogenase (forward direction), glucose-6-phosphate dehydrogenase, pyruvate dehydrogenase and alcohol dehydrogenase have none.
- **Optima:** most "temperature optima" are assay temperatures. The real ones are for purified enzymes and lie far above growth temperature (aldolase 57 °C, GAPDH 55 °C, acetate kinase about 70 °C).
- **Wrong EC numbers in the old list:** 2.7.1.1 (hexokinase; *E. coli* has none, glucokinase is 2.7.1.2), 2.6.1.11 (acetylornithine transaminase, labelled alanine aminotransferase, which is 2.6.1.2), 7.1.1.7 (cytochrome *bd*, labelled *bo3*, which is 7.1.1.3), and 2.3.3.1 (BRENDA files *E. coli* citrate synthase under 2.3.3.16).
- **Wrong reactions:** the old seed attached each EC to the first reaction carrying it. 11 of 32 rows matched no reaction and never affected a simulation; phosphofructokinase went to PFK_3 (sedoheptulose), hexokinase to HEX4 (mannose), and the "alanine aminotransferase" value to ACOTA.

## Why the engine no longer uses kcat

The old bound was `TPM × kcat × activity(T, pH) × 1e-4`. TPM measures RNA, not enzyme, and 1e-4 was never derived from data. Wild-type growth on glucose at 37 °C, pH 7 (iML1515, glucose uptake 10 mmol/gDW/h; measured growth is about 0.6–0.7 1/h):

| Kinetics used | Growth (1/h) | Reactions that limit growth |
| --- | --- | --- |
| None (plain FBA) | 0.88 | — |
| Old unsourced values | 0.86 | PFK_3, ACONTb |
| BRENDA values | 0.31 | AKGDH, LDH_D, PFL, ACKr, NADH16pp, ATPS4rpp |
| BRENDA + gaps filled from Davidi et al. 2016 | 0.31 | as above, plus GAPD |
| Same, kcat only (optima ignored) | 0.70 | FBA, AKGDH, SUCDi, PFL, PTAr, NADH16pp, ATPS4rpp, PGI, … |
| Protein copies per cell (Schmidt et al. 2016) × kcat | 0.18 | SUCDi, PFL, NADH16pp, ATPS4rpp, PGI, … |

The last row is the standard enzyme-constrained approach (as in GECKO). It needs careful curation of complex stoichiometry and membrane proteins, which proteomics under-detect, so it is future work.

The old values happened to be large enough that the formula seldom bound. With real values it does, so the old full-engine growth results partly rested on two unsourced numbers (aconitase 18, aldolase 20).

**Decision:** kinetic caps are off (`USE_KINETIC_CAPS = False` in `bound_compiler.py`). Every reaction uses the expression-relative bound (E-Flux style). Temperature and pH act through substrate uptake, with an assumed optimum of 37 °C and pH 7. Set the flag to `True` only to reproduce the old behaviour as a sensitivity check.

## References

- Chang A et al. (2021) BRENDA, the ELIXIR core data resource in 2021. *Nucleic Acids Research* 49:D498–D508.
- Davidi D et al. (2016) Global characterization of in vivo enzyme catalytic rates and their correspondence to in vitro kcat measurements. *PNAS* 113(12):3401–3406.
- Schmidt A et al. (2016) The quantitative and condition-dependent *Escherichia coli* proteome. *Nature Biotechnology* 34:104–110.
- Sánchez BJ et al. (2017) GECKO. *Molecular Systems Biology* 13:935.
- Colijn C et al. (2009) E-Flux. *PLoS Computational Biology* 5(8):e1000489.
