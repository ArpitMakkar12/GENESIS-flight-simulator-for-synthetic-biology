# Kinetics curation protocol (GENESIS, step 4A)

Source: BRENDA (https://www.brenda-enzymes.org), accessed 1 November 2026.
Page per EC number: https://www.brenda-enzymes.org/enzyme.php?ecno=<EC>&organism_list=Escherichia+coli
(When that page was cut off or failed, the single-table views were used instead:
https://www.brenda-enzymes.org/all_enzymes.php?ecno=<EC>&table=Turnover_Number, Temperature_Optimum or pH_Optimum, keeping only E. coli rows.)
Reference details: https://www.brenda-enzymes.org/literature.php?e=<EC>&r=<BRENDA reference ID>

The engine uses only three numbers per enzyme: kcat (1/s), optimum temperature (°C), optimum pH.

## Rules (apply mechanically; never pick a value because it "looks right")

1. Organism: *Escherichia coli* entries only (any strain; note the strain if BRENDA gives it).
2. kcat (TURNOVER NUMBER [1/s]):
   - wild-type enzyme only; drop every mutant entry;
   - natural forward substrate only (the substrate listed for that EC below); drop analogues, alternative substrates and entries measured with analogue co-substrates;
   - keep values measured at 25–37 °C, or with no temperature stated;
   - isoenzymes (e.g. PykF/PykA): pool their wild-type values and say so in notes;
   - take the MEDIAN of the kept values; record n, min, max, and every BRENDA reference ID used;
   - if no value passes the 25–37 °C filter, use all wild-type natural-substrate values and write "temp filter relaxed" in notes;
   - if nothing qualifies at all, leave kcat empty and write "no E. coli wild-type kcat".
3. Temperature optimum: E. coli wild-type entries; median if several; a range "a–b" counts as its midpoint. None → leave empty ("no data"). Never fill in 37.
4. pH optimum: E. coli wild-type, forward reaction direction where BRENDA says; range → midpoint; median if several. None → leave empty.
5. For every reference ID used in a chosen value, resolve: first author, year, PubMed ID.
6. Report BRENDA's recommended enzyme name for the EC, so wrong EC numbers are caught.

## Output: one CSV row per EC (header exactly)

ec,brenda_name,substrate,kcat_median,kcat_n,kcat_min,kcat_max,kcat_refs,temp_opt,temp_refs,ph_opt,ph_refs,references,notes

- *_refs: BRENDA reference IDs separated by spaces
- references: "ID=FirstAuthor Year PMID" separated by "; "
- quote any field containing a comma

## Amendments made after the first pass (apply to the final table)

- **"Assay at" entries are not optima.** BRENDA files some assay conditions under its optimum sections and marks them "assay at" or "activity assay". They are left out of temp_opt and ph_opt. Only `kinetics_curated.csv` (backend) and the `*_nonassay` columns of `all_36_ec_numbers.csv` reflect this; the per-batch notes in AUDIT.md still mention them.
- **Citrate synthase:** BRENDA files *E. coli* GltA under EC 2.3.3.16, not 2.3.3.1. Its two wild-type oxaloacetate values (81, 92) were used: median 86.5.
- **Succinate dehydrogenase (1.3.5.1):** rows from fumarate reductase papers (a different enzyme, EC 1.3.5.4) were dropped.
- **Reaction mapping:** each value is attached to a named iML1515 reaction (BiGG ID), chosen by hand from the enzyme, not by EC lookup.
