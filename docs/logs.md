# GENESIS — Project Progress Log

> **Last updated:** 2026-10-16

This log records what was built, when, and why: the decisions behind the design, the problems found along the way and how they were fixed. It is compiled from the git history; commit hashes are given so any entry can be traced to the code. Update it at the end of every work session, before pushing.

For installation and usage, see the [README](../README.md).

---

## Status at a glance

| Phase | Scope | Status |
| --- | --- | --- |
| Foundation | Monorepo, Docker Compose, migrations, CI | Complete |
| Data layer | Genome, metabolic model, regulation, kinetics, parts | Complete |
| Simulation pipeline | Regulators → expression → bounds → flux balance analysis | Complete |
| AI expression engine | Measured lookup for known genes, HyenaDNA model for novel DNA, RBS calculator | Complete |
| Application | Simulate, Results, Compare, Export, Library, Home | Complete |
| Validation | Essential genes and growth rates against PRECISE-1K | Complete |
| Gene knockouts | Delete genes, compare with the wild type, show the track record | Complete |
| Tests and CI | 48 backend and 14 frontend tests; CI fails on a failing test | Complete |
| Reproducibility | One-command database setup and a full README | Complete; clean-clone test pending |
| Enzyme-constrained model | Predict overflow metabolism | Planned |

---

## Progress timeline

### 2026-09-01 to 09-02 — Foundation

- Monorepo created: FastAPI backend, AI module, Next.js frontend, shared interface contracts, Docker Compose with PostgreSQL 16 and Redis 7 (`9f3f3fa`).
- Alembic migration creating all tables; GitHub Actions CI; Dockerfile fixed for COBRApy (`5ba0c3a`).
- iML1515 verified with COBRApy: 2,712 reactions, 0.877 h⁻¹ maximum growth on its default medium.
- Fixes: the PyPI package is `cobra`, not `cobrapy`; frontend `.dockerignore`; a Pydantic namespace warning (`571c5e9`).

### 2026-09-02 — Data seeding

Seed scripts in `backend/app/data/` load real biological data (`706cede`):

| Script | Table | Rows | Source |
| --- | --- | --- | --- |
| `seed_genome.py` | genes | 4,651 | NCBI RefSeq NC_000913.3 |
| `seed_reactions.py` | reactions, enzyme_reactions | 2,712 / 4,754 | iML1515 |
| `seed_regulondb.py` | transcription_factors, gene_regulations | 20 / 38 | RegulonDB (curated core set) |
| `seed_brenda.py` | enzyme_kinetics | 32 | BRENDA (curated central-metabolism enzymes) |
| `seed_tcdb.py` | transporters | 26 | TCDB |
| `seed_igem.py` | genetic_parts | 23 | iGEM Registry |

### 2026-09-04 — APIs and first connected frontend

- Knowledge API (gene search by name, locus tag or product; transcription factors; pathways), Parts API (filters, search, pagination, detail) and Results API (`028265e`).
- Frontend Knowledge and Parts pages connected to live data; TypeScript and ESLint errors fixed (`a38a121`, `ed61503`).
- Progress log added (`8131a5c`).

### 2026-09-06 — Contract and schema fixes

- Schema drift between models and seed scripts repaired; `enzyme_kinetics.reaction_id` made nullable (PR #1).
- Interface contract corrected: `gene_ids` added to `PredictionInput`; `relative_expression` redefined as fold change versus reference; `reference_expression_tpm` added for flux unit conversion; RBS scoring moved inside the AI layer; `prediction_source` added for transparency (`590456b`).
- Model files moved to a bind mount (`./data/models`).

### 2026-09-14 to 09-15 — AI groundwork

- Stub predictor implementing the contract, so the pipeline could be built end to end; input validation returns warnings rather than failing a whole run (PR #2).
- Sequence matcher: identifies whether submitted DNA is a known gene, a known gene with edits, or novel (PR #3).
- PRECISE-1K data inspection (PR #4) and a HyenaDNA wrapper with a CPU benchmark (PR #5).

### 2026-09-18 to 09-21 — Simulation pipeline

- Core orchestrator (`SimulationRunner`), environment-responsive transcription-factor resolver, bound compiler (expression → reaction bounds) and COBRApy FBA solver for iML1515 (PRs #6–#13).
- `POST /simulate` wired to the full pipeline; every run persisted to the `simulations` table (`9ad2e83`, `0d887d5`).
- PRECISE-1K seed scripts: measured expression for 4,351 genes and a 10,783-interaction regulatory network (`02516ec`).
- Constructs API; DNA sequence parser with ORF detection on both strands and 300 bp promoter extraction; 9 end-to-end tests passing (`0d887d5`).
- Missing migration for `reference_expression_tpm` added; promoter–expression training dataset built (PRs #14, #15).

### 2026-09-30 — Application redesign

- Interface reskinned in a dark-field microscopy theme across all pages, with shared Card, MetricCard, StatusBadge and loading components (`40fdd02`).
- Results system: browse page with filters and deletion, detail page, side-by-side comparison, flux map, process trace and Markdown export.
- Simulate page restructured around a single parameter state, five shared presets and protection against changes during a running simulation; home page hero.
- Parts and Knowledge restructured with explicit field states (populated, not applicable, pending); coding-part sequences backfilled from the iGEM Registry with SHA-256 verification; promoter annotations corrected; Playwright and integrity tests (`940035e`).

### 2026-10-01 to 10-02 — AI expression engine

- **Two-track prediction** (`a4e4b36`, `f463009`):
  - known genes resolve to measured PRECISE-1K expression (confidence 0.85)
  - novel sequences go through HyenaDNA embeddings and a trained ensemble (confidence 0.35)
- **Environment response:** comes from transcription-factor state, applied through the 10,783 regulator–gene interactions. Effects sum in log space, are damped by √n and are capped at 16×.
- **Verified biology:**
  - dnaK and groEL rise 2× under heat shock
  - lacZ rises 2× on lactose
  - FNR and ArcA targets fall to 0.5× without oxygen
- **Expression model:** HyenaDNA embeddings of 4,331 promoters, reduced by PCA and combined with 29 hand-built promoter features; ridge and gradient boosting ensembled.
  - Held-out Pearson r = 0.378 on 866 unseen genes.
  - Embeddings alone score 0.345 and hand features alone 0.223, so the foundation model contributes real signal.
- **RBS calculator:** thermodynamic translation initiation via ViennaRNA. It reproduces the known ~100× strength difference between BBa_B0034 and BBa_B0033 (177× after the correction below).
- **Pre-handover audit fixes** (`0f35d72`):
  - `rbs_score` was never returned; it is now wired in.
  - The RBS energy model double-counted mRNA unfolding; it now uses a net binding energy over the ribosome footprint.
  - CRP and FNR were spelled differently in two seed sources, leaving 556 CRP and 323 FNR edges unreachable. Matching is now case-insensitive, and environment-responsive genes rose from 951 to 1,293.
- **Integration** (`064b59d`):
  - All 1,514 enzyme-linked genes with measured expression now drive flux bounds; 2,229 of 2,712 reactions (82%) are constrained by expression.
  - Simulations take 458–843 ms against a 2,000 ms budget.
- **Known limitation documented** (`8f1b85c`): lactose and heat shock predicted faster growth than reference, because higher expression only ever loosened bounds.

### 2026-10-05 to 10-06 — Test-report fixes

- **Growth-direction defect fixed** (`2fe499e`).
  - The cause: the bound compiler took the minimum over all of a reaction's genes, so for isozymes the weaker gene set the cap, and reference growth was 0.288 h⁻¹ against iML1515's 0.877.
  - The fix: gene rules are now evaluated properly (AND → minimum, OR → sum). Reference growth is 0.802 h⁻¹, and regulation moves growth by at most about 2%.
- **Temperature and pH** (`336ce23`, `2fe499e`):
  - Uptake bounds now scale with enzyme activity at the chosen temperature and pH.
  - A thermal collapse above 46 °C makes 50 °C near-lethal.
  - Viability falls with temperature.
- **Reporting:**
  - growth state (optimal, slowed, stressed, not viable) judged against the reference
  - a three-way explanation when growth fails (biological, environmental or constraint)
  - regulator state and changes
  - all non-zero fluxes, split up/down gene lists, and correct timestamps
- **Expression for custom DNA in Docker** (`d24d1f0`):
  - CPU PyTorch, transformers and scikit-learn added to the backend image.
  - `fetch_hyenadna.py` downloads the encoder.
  - The models preload at startup.
  - Curated regulatory edges deleted by the PRECISE import are restored.
  - IclR and Cra rules added.
- Emojis replaced with Lucide icons throughout the interface (`4e142f2`).

### 2026-10-08 to 10-12 — Results, Library and interface

- **Results:**
  - select and delete several runs at once (`887b2cc`)
  - permanent run numbers, editable names, pagination and one formatting standard across pages (`ed41253`)
  - search by name, run number, carbon source, oxygen, temperature and pH (`6a9dbc2`)
- **Flux map** draws real FBA fluxes for every carbon source, with arrows that reverse when a pathway runs backwards (`b178aae`).
- **Comparison:** per-metric charts and clearer growth-versus-reference labels (`037a000`).
- **Export:** PDF reports for single runs and comparisons (`35fe304`).
- **Gene expression panel:** Up/Down/All tabs, search across every gene, a paged list and a clearer process trace (`db4793f`); animated copy button for the raw JSON (`ccb08c3`).
- **Library:**
  - Parts and Knowledge merged into one Library page with its own navigation entry and links from results and the Simulate page (`2e87e47`)
  - every part type shows the right strength or role: inducible, T7, RBS, terminator, coding (`98fc9ee`)
  - genes, transcription factors and pathways paged, with one search box across tabs (`0a05a2c`, `a73fbc8`, `9c017e0`, `74ecff9`)
- **Home and navigation:**
  - a readout strip, a connected pipeline view and recent runs on the home page (`e15da33`)
  - a cell logo mark and glowing active-page indicator in the navbar (`d8cc05e`)

### 2026-10-15 — Validation against published experiments

Both checks use PRECISE-1K (Lamoureux et al., *Nucleic Acids Research* 2023), pinned to a fixed commit (`102d054`).

- **Essential genes.** All 1,516 model genes are deleted in turn on a rich medium approximating LB broth, the condition the laboratory data was measured in.
  - Precision 0.800, recall 0.694, F1 0.743, **MCC 0.725** (84 TP, 21 FP, 37 FN, 1,372 TN).
  - Unchanged at every cut-off from 1% to 25% and at every nutrient uptake rate tested.
- **Growth rates.** Six measured wild-type conditions. The first run showed every sugar receiving the same carbon supply, so glycerol was predicted fastest when it is among the slowest.
- **Measured uptake rates:**
  - the flat 60 C-mmol carbon supply replaced by measured rates from Gerosa et al. 2015 (`fbdf25a`)
  - xylose from Gonzalez et al. 2017 (`53803b0`)
  - both are independent of the validation data

| Full engine | Mean absolute error | Bias | Spearman | Pearson |
| --- | --- | --- | --- | --- |
| Before measured uptake | 0.205 h⁻¹ | +0.147 | −0.03 | 0.59 |
| Gerosa rates | 0.131 h⁻¹ | +0.071 | 0.66 | 0.80 |
| Plus measured xylose | **0.111 h⁻¹** | +0.051 | **0.71** | **0.85** |

- **Overflow metabolism documented as a known limitation** (`99a4380`). Fast sugars run 20–35% high because flux balance analysis cannot predict acetate secretion. Forcing the measured acetate output would improve the numbers but hard-code an output the engine should predict, so it was left visible and an enzyme-constrained model was planned instead.

### 2026-10-16 — Gene knockouts, tests and reproducibility

- **Gene knockouts** (`977de84`):
  - `knockout_genes` on `POST /simulate` deletes up to 10 of the 1,516 model genes, and the same run also solves the wild type with identical regulators, expression and medium.
  - The Simulate page has a ranked gene picker.
  - The results page shows growth before and after, each gene's track record against the laboratory essentiality data, and the pathways that switched off or shifted.
  - Examples: Δeno grows at 0.664 against 0.802 (−17%) by rerouting through serine, a known model miss since the lab finds eno essential. ΔgltA stops growth on glucose minimal medium, which is correct even though the gene is dispensable in LB.
- **Backend tests** (`b3153de`): 48 pytest tests covering growth-state thresholds, uptake limits, regulator rules, FBA on iML1515 including knockouts, the essentiality records and an end-to-end API run with a stub predictor. CI no longer ignores failures.
- **Frontend tests** (`0be11dd`): Vitest added, with 14 tests checking the flux map's pentose-phosphate carbon arithmetic against seven real iML1515 solutions, including three alternative routes the solver was forced to take.
- **Documentation and setup:**
  - README rewritten as a complete project overview, and the project renamed from BioSandbox to GENESIS (`27130e0`)
  - one-command database setup, `python -m app.data.setup`: every step in a safe order, followed by checks on every table

---

## Architecture decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Organism | *E. coli* K-12 MG1655 only | Best characterised organism, with the most data available |
| Database | PostgreSQL only | The regulatory graph fits join tables; no separate graph database needed |
| Metabolic model | iML1515 with COBRApy and GLPK | The current genome-scale reconstruction for K-12 |
| Expression for known genes | Measured PRECISE-1K values | Real measurements beat a model with r = 0.378 |
| Expression for novel DNA | HyenaDNA embeddings + ridge/gradient-boosting ensemble | Single-nucleotide resolution, runs on CPU |
| Environment response | Transcription-factor state, not the sequence model | The sequence model cannot see the environment; regulators can |
| Inference | PyTorch and scikit-learn on CPU | ONNX export was tested, but the gradient-boosting model does not export |
| Expression to flux | Gene–protein–reaction rules (AND → min, OR → sum) | Taking a plain minimum let one isozyme cap a whole reaction |
| Carbon uptake | Measured rates where published, 60 C-mmol otherwise; aerobic only | A flat carbon supply mis-ranked carbon sources |
| Knockouts | A field on `/simulate`, wild type solved in the same run | One run, identical conditions, so differences come from the deletion alone |
| Validation | PRECISE-1K pinned to one commit; LB-like medium for essentiality | Results cannot drift; matches the conditions of the laboratory data |
| Tests | Stub predictor in tests | CI has no model files; tests target the engine and the API |
| Setup | One script in a fixed order, with checks | Seed scripts skip non-empty tables, so the wrong order leaves silent gaps |
| `reaction_formula` column | `TEXT` instead of `VARCHAR(1000)` | Some iML1515 formulas exceed 1,000 characters |

---

## Database summary

```
genes (4,651; 4,351 with measured expression)
├── locus_tag, name, product, position, strand, sequences, GC content
├── reference_expression_tpm, expression_source
│
├── → enzyme_reactions (4,754) → reactions (2,712; 40 pathways)
│     └── bigg_id, name, subsystem, formula, EC number, bounds
│
├── → gene_regulations (10,783) ← transcription_factors (371; 20 with condition rules)
│     └── regulation type, confidence
│
├── → transporters (26)
│
├── enzyme_kinetics (32) → reactions
│     └── Km, kcat, optimal temperature and pH
│
├── genetic_parts (23)
├── constructs → construct_parts
└── simulations
      └── run_number, name, conditions, growth, fluxes,
          expression (top changes and all genes), knockout comparison
```

---

## Setup

Full instructions are in the [README](../README.md#getting-started). In short:

```bash
docker compose up --build -d
docker compose exec backend python -m app.data.setup
docker compose restart backend
```

---

## Workflow

```
Start of a session     git pull origin main
During                 small commits with descriptive messages
Before pushing         run the tests:
                         docker compose exec -e DEBUG=false backend python -m pytest
                         docker compose exec frontend npm test
                       update this log
End of a session       git pull origin main && git push origin main
```

---

## Known issues and gotchas

1. **Docker `version` warning.** `docker-compose.yml` still has `version: '3.8'`; Compose ignores it, and the warning is cosmetic.
2. **RegulonDB SSL.** Direct download fails on certificate verification; setup uses the built-in curated set of 20 core regulators, and PRECISE-1K supplies the full network.
3. **BRENDA.** Bulk download requires registration; a curated set of 32 central-metabolism enzymes is used.
4. **BiGG redirect.** `cobra.io.load_model('iML1515')` fails on an HTTP→HTTPS redirect; the SBML file is downloaded directly.
5. **libexpat1** must be in the backend image for COBRApy and libSBML.
6. **Restart after seeding.** The backend reads the database once at startup; run `docker compose restart backend` after setup.
7. **Frontend dependencies.** The frontend container keeps its own `node_modules`. After changing `package.json`, run `docker compose up --build -V frontend`, and `npm install` on the host so the editor sees the new packages.
8. **PowerShell 5.1** shows UTF-8 characters such as "—" garbled in API responses. This is a display problem only; the browser and PowerShell 7 show them correctly.
9. **Model limitations**, documented in the validation reports:
   - Fast sugars run high (overflow metabolism).
   - Glucose at 42 °C is predicted below 37 °C.
   - On galactose, a microaerobic run can out-grow an aerobic one, because only an aerobic uptake rate has been measured.
   - Anaerobic growth and the pH response are not yet validated (no data in PRECISE-1K).

---

## Next steps

- **Clean-clone test.** Follow the README on a fresh clone and fix any gap found.
- **Enzyme-constrained model.** Predict overflow metabolism instead of overestimating growth on fast sugars.
- **Temperature validation.** Check the heat response against independent temperature–growth data.
- **Minimal-medium essentiality.** Validate knockouts on glucose minimal medium, the condition users simulate most.
- **Strains.** BW25113 and other laboratory strains as preset sets of gene differences from MG1655.
  - **Naming.** Done: API title, health check, startup messages and CI now say GENESIS. The local database keeps the name `biosandbox`, so existing volumes keep working; the online database will be named `genesis`.