# GENESIS

**A flight simulator for synthetic biology.**

GENESIS simulates how *Escherichia coli* K-12 MG1655 responds to its environment, to engineered DNA and to gene deletions, before anything is built in the lab. Set the temperature, pH, oxygen and carbon source, optionally paste a genetic part or delete genes, and GENESIS predicts which regulators switch on, how the cell's metabolic genes change their expression, how carbon flows through metabolism, and how fast the cell grows.

Every prediction is explained step by step, and the engine is checked against published experiments: it identifies essential genes with a Matthews correlation of **0.725** and predicts growth rates on six measured conditions within **0.11 h⁻¹** on average ([Validation](#validation)).

[![CI](https://github.com/ArpitMakkar12/GENESIS-flight-simulator-for-synthetic-biology/actions/workflows/ci.yml/badge.svg)](https://github.com/ArpitMakkar12/GENESIS-flight-simulator-for-synthetic-biology/actions/workflows/ci.yml)

---

## Contents

- [What you can do](#what-you-can-do)
- [How a simulation works](#how-a-simulation-works)
- [Validation](#validation)
- [Getting started](#getting-started)
- [Project structure](#project-structure)
- [API](#api)
- [Testing and CI](#testing-and-ci)
- [Tech stack](#tech-stack)
- [Data sources and references](#data-sources-and-references)
- [Scope and limitations](#scope-and-limitations)
- [Roadmap](#roadmap)
- [Team](#team)

---

## What you can do

| Area | What it offers |
| --- | --- |
| **Simulate** | Set temperature (20–50 °C), pH (4–9), oxygen (aerobic, microaerobic, anaerobic), carbon source (9 options) and nitrogen source, or start from a preset (Reference, Anaerobic, Heat Shock, Acid Stress, Glycerol Feed). Optionally paste DNA or load a part from the Library. A run takes about one to two seconds. |
| **Gene knockouts** | Delete up to 10 of the 1,516 metabolic genes. Each run also solves the unmodified cell (the wild type) under identical conditions, so the result shows exactly what the deletion changed: growth before and after, the pathways that switched off or shifted, and each gene's track record against laboratory essentiality data. |
| **Results** | Every run is saved with a permanent number. Its page shows growth rate, doubling time and viability; why growth failed, if it did; a step-by-step trace of the pipeline; a carbon-flow map drawn from the actual fluxes; bottleneck reactions; and searchable predictions for every gene. |
| **Compare** | Put up to four runs side by side: growth, flux maps and the pathways that differ once the difference in growth is allowed for. |
| **Export** | Download any run or comparison as Markdown or PDF for a lab notebook. |
| **Library** | Browse the knowledge behind the engine: 23 characterised genetic parts, 4,651 genes, 371 transcription factors and their targets, and 40 metabolic pathways, with links from results straight to the relevant entry. |

---

## How a simulation works

```
 Environment ──► 1. Regulators ──► 2. Gene expression ──► 3. Reaction limits ──► 4. Flux balance ──► Growth,
 (T, pH, O₂,        which TFs          fold change for         expression and         analysis on         fluxes,
  carbon, N)        are active         metabolic genes         temperature/pH         iML1515             pathways
 + your DNA                                                     → bounds
 + knockouts ─────────────────────────────────────────────────────────────────────────► (genes removed)
```

1. **Regulators.** Rules for well-characterised master regulators (CRP, FNR, ArcA, RpoH, RpoS and others) decide which transcription factors are active in the chosen environment. The other regulators default to active.
2. **Gene expression.** For each metabolic gene, the measured baseline from PRECISE-1K is shifted by its active regulators through a network of 10,783 regulatory interactions. DNA pasted on the Simulate page that matches no known gene is scored by a HyenaDNA sequence encoder and a trained expression model.
3. **Reaction limits.** Expression levels become upper bounds on the reactions each enzyme catalyses, following the model's gene–protein–reaction rules (isozymes add up; enzyme complexes are limited by their scarcest subunit). Enzyme activity is scaled for temperature and pH, with heat collapse above 46 °C.
4. **Flux balance analysis.** The medium sets how much carbon and oxygen the cell can take up. Carbon uptake limits are measured rates from published experiments where they exist. COBRApy then solves the genome-scale model iML1515 (2,712 reactions, 1,516 genes) for maximum growth. Knocked-out genes switch off every reaction that has no backup enzyme.

The result reports growth rate, doubling time, viability, the active pathways and the binding constraints. When the cell cannot grow, it says why: the medium, the temperature or pH, the expression limits, or a knockout.

---

## Validation

A simulator is only useful if it agrees with real cells. Two checks compare GENESIS with [PRECISE-1K](https://github.com/SBRG/precise1k) (Lamoureux et al., *Nucleic Acids Research* 2023), pinned to a fixed commit so the results cannot drift.

**Essential genes.** Each of the 1,516 model genes is deleted in turn on a rich medium approximating LB broth, the condition the laboratory data was measured in.

| Precision | Recall | F1 | MCC |
| --- | --- | --- | --- |
| 0.800 | 0.694 | 0.743 | **0.725** |

84 true positives, 21 false positives, 37 false negatives and 1,372 true negatives. The result is unchanged at every lethality cut-off from 1% to 25% and at every nutrient uptake rate tested.

**Growth rates.** The full engine predicts wild-type growth on six measured conditions: glucose at 37 °C and 42 °C, fructose, xylose, glycerol and acetate.

| Engine | Mean absolute error | Bias | Spearman | Pearson |
| --- | --- | --- | --- | --- |
| GENESIS (full engine) | **0.111 h⁻¹** | +0.051 h⁻¹ | 0.71 | 0.85 |

Carbon uptake limits come from independent studies (Gerosa et al. 2015; Gonzalez et al. 2017), never from the validation data, so the check cannot grade itself.

**Known limitations, stated in the reports:**
- Fast sugars run high. Real *E. coli* growing fast secretes part of its sugar as acetate (overflow metabolism), which flux balance analysis cannot predict. An enzyme-constrained model is the planned fix.
- The heat penalty is the main ranking error: glucose at 42 °C is predicted below glucose at 37 °C.
- PRECISE-1K has no anaerobic growth rates and only pH 7 experiments, so those responses are not yet validated.

Full reports, per-gene results and charts are in [`backend/validation/results/`](backend/validation/results/). The method is described in [`backend/validation/README.md`](backend/validation/README.md).

---

## Getting started

### Requirements

- Docker Desktop (or Docker Engine with Compose v2) and git
- About 5 GB of free disk space; the backend image includes PyTorch
- An internet connection for the first setup
- Free ports 3000, 8000, 5432 and 6379

### Install

```bash
git clone https://github.com/ArpitMakkar12/GENESIS-flight-simulator-for-synthetic-biology.git genesis
cd genesis

docker compose up --build -d                          # first build: 5–10 minutes
docker compose exec backend python -m app.data.setup  # 3–5 minutes, downloads about 20 MB
docker compose restart backend                        # the app reads the data once, at startup
```

Then open **http://localhost:3000**. Use exactly `localhost`: the frontend calls the API at `http://localhost:8000`, and the API only accepts requests from `http://localhost:3000`. Interactive API documentation is at http://localhost:8000/docs.

No `.env` file is needed: `docker-compose.yml` sets every variable. `.env.example` only matters if you run the backend outside Docker.

### What setup does

`app.data.setup` runs every step in the only order that works, then checks each table and reports anything that is short. It is safe to run again: finished steps are skipped.

| Step | Fills | Source |
| --- | --- | --- |
| Migrations | all tables | `backend/migrations/` |
| Metabolic model | `data/models/iML1515.xml.gz` | BiGG Models |
| Genome | 4,651 genes | NCBI RefSeq NC_000913.3 |
| Reactions | 2,712 reactions and 4,754 gene–reaction links | iML1515 |
| Pathway names | reaction subsystems (40 pathways) | BiGG Models (iML1515 JSON) |
| Regulators | 20 core regulators with condition rules | RegulonDB, with a built-in curated fallback |
| Kinetics, transporters, parts | enzyme kinetics, 26 transporters, 23 genetic parts | BRENDA, TCDB, iGEM Registry (curated, built in) |
| Part sequences | full DNA for coding parts | `backend/app/data/registry_sequences.json` (checksummed) |
| PRECISE-1K | measured expression for 4,351 genes; 10,783 regulatory interactions | SBRG/precise1k |

### Optional: predictions for your own DNA

The steps above cover every built-in gene and part. Only DNA you paste on the Simulate page that matches no known gene needs the AI models; without them, such DNA is scored at the median expression with low confidence. To build them (HyenaDNA is about 16 MB; encoding takes about two minutes):

```bash
docker compose exec backend python fetch_hyenadna.py
docker compose exec backend python -m app.data.seed_genome_sequence
docker compose exec backend python -m app.data.build_training_data
docker compose exec backend python ai/training/encode_promoters.py
docker compose exec backend python ai/training/train_expression_v2.py
docker compose restart backend
```

### Troubleshooting

- **"Failed to download from RegulonDB: … CERTIFICATE_VERIFY_FAILED"** is expected: RegulonDB's certificate does not verify. Setup falls back to a built-in curated set of 20 core regulators, and PRECISE-1K then adds the full network.
- **A setup check fails** after an earlier attempt ran steps out of order: run `docker compose down -v` (this deletes the database, including saved runs), then `docker compose up -d` and run setup again.
- **The app shows no genes or pathways:** run `docker compose restart backend` after setup.
- **"Port is already allocated":** another service is using 5432, 6379, 3000 or 8000. Stop it, or map different host ports in a `docker-compose.override.yml`.
- **After changing `frontend/package.json`:** run `docker compose up --build -V frontend`, because the container keeps its own `node_modules`.

---

## Project structure

```
genesis/
├── backend/                     FastAPI service: API, simulation engine, data
│   ├── app/
│   │   ├── api/                 REST endpoints (simulate, results, knockout, knowledge, parts, export)
│   │   ├── services/            Simulation pipeline: TF resolver, bound compiler, FBA solver, runner
│   │   ├── models/              SQLAlchemy tables
│   │   ├── schemas/             Request and response models
│   │   └── data/                Seed scripts and setup.py (one-command database setup)
│   ├── migrations/              Alembic migrations
│   ├── validation/              Essential-gene and growth-rate checks against PRECISE-1K
│   └── tests/                   pytest suite
├── ai/                          Expression prediction
│   ├── inference/               Predictor, sequence matcher, environment conditioner
│   ├── models/                  HyenaDNA wrapper, expression model, model registry
│   └── training/                Training-data encoding and model training
├── contracts/                   Interfaces shared by the backend and the AI module
├── frontend/                    Next.js application
│   └── src/
│       ├── app/                 Pages: home, simulate, results, compare, library
│       ├── components/          Flux map, knockout picker, gene expression panel, ...
│       └── lib/                 Formatting, pathway comparison, flux arithmetic (unit tested)
├── tests/                       End-to-end scripts run against a live stack
├── docs/                        Design notes and development log
├── .github/workflows/ci.yml     Continuous integration
└── docker-compose.yml           Database, cache, backend and frontend
```

Downloaded and generated data (`data/`, `backend/data/`, model weights) is not committed; `app.data.setup` and the optional model commands recreate it.

---

## API

All endpoints are under `http://localhost:8000/api/v1`. Full schemas are at `/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/simulate` | Run a simulation: environment, optional DNA, optional `knockout_genes` |
| `GET` | `/results` | Saved runs, paged, with filters, search and sorting |
| `GET` | `/results/{id}` | One run in full, including pathway totals and any knockout comparison |
| `GET` | `/results/{id}/genes` | Search and page through every gene prediction of a run |
| `PATCH` · `DELETE` | `/results/{id}` | Rename or delete a run |
| `POST` | `/results/bulk-delete` | Delete several runs |
| `GET` | `/knockout/genes` | Search the metabolic genes that can be knocked out, with essentiality records |
| `GET` | `/genes`, `/genes/{locus_tag}` | Genes |
| `GET` | `/tfs`, `/tfs/{name}` | Transcription factors and their targets |
| `GET` | `/pathways`, `/pathways/{subsystem}` | Metabolic pathways and their reactions |
| `GET` | `/parts`, `/parts/{name}` | Characterised genetic parts |
| `POST` | `/export/pdf` | Render a report as PDF |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{"temperature": 37, "ph": 7, "oxygen_level": "aerobic", "carbon_source": "glucose", "knockout_genes": ["b2779"]}'
```

---

## Testing and CI

```bash
docker compose exec backend pip install -r requirements-dev.txt   # once per image build
docker compose exec -e DEBUG=false backend python -m pytest        # 48 backend tests
docker compose exec frontend npm test                              # 14 frontend tests
docker compose exec backend python -m validation.essentiality      # validation reports
docker compose exec backend python -m validation.growth_rates
```

- **Backend tests** cover growth-state thresholds, carbon uptake limits, regulator rules, flux balance analysis on iML1515 (wild type, media and knockouts), the essentiality records and an end-to-end API run.
- **Frontend tests** check the flux map's carbon arithmetic against seven real iML1515 solutions, including routes the solver was forced to take.

GitHub Actions runs both suites and a production build of the frontend on every push and pull request to `main` and `dev`. A failing test fails the build.

---

## Tech stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts, Lucide icons, Vitest |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic 2, WeasyPrint (PDF export) |
| Simulation | COBRApy with the GLPK solver, iML1515 genome-scale model |
| AI | PyTorch (CPU), HyenaDNA (small, 32k context), scikit-learn expression model |
| Data | PostgreSQL 16; Redis 7 is provisioned for a future job queue |
| Infrastructure | Docker Compose, GitHub Actions |

---

## Data sources and references

| Source | Used for |
| --- | --- |
| [iML1515](http://bigg.ucsd.edu/models/iML1515), Monk et al., *Nature Biotechnology* 35:904–908 (2017) | Genome-scale metabolic model |
| [PRECISE-1K](https://github.com/SBRG/precise1k), Lamoureux et al., *Nucleic Acids Research* 51(19):10176 (2023), [doi:10.1093/nar/gkad750](https://doi.org/10.1093/nar/gkad750) | Reference expression, regulatory network, validation ground truth |
| [NCBI RefSeq NC_000913.3](https://www.ncbi.nlm.nih.gov/nuccore/NC_000913.3) | *E. coli* K-12 MG1655 genome |
| [RegulonDB](https://regulondb.ccg.unam.mx/) | Core transcription-factor rules |
| [BRENDA](https://www.brenda-enzymes.org/) | Enzyme kinetics, temperature and pH optima |
| [TCDB](https://www.tcdb.org/) | Transporter classification |
| [iGEM Registry](https://parts.igem.org/) | Characterised genetic parts and sequences |
| Gerosa et al., *Cell Systems* 1(4):270–282 (2015), [doi:10.1016/j.cels.2015.09.008](https://doi.org/10.1016/j.cels.2015.09.008) | Measured carbon uptake rates |
| Gonzalez, Long & Antoniewicz, *Metabolic Engineering* 39:9–18 (2017), [doi:10.1016/j.ymben.2016.11.003](https://doi.org/10.1016/j.ymben.2016.11.003) | Measured xylose uptake rate |
| HyenaDNA, Nguyen et al., NeurIPS 2023 | DNA sequence encoder for novel parts |

---

## Scope and limitations

GENESIS predicts the metabolic consequences of environmental conditions and complete gene knockouts in *E. coli*. It is a tool for exploring hypotheses and narrowing down experiments, not a replacement for them.

- **Metabolism only.** Genes outside metabolism, such as those for replication, transcription, translation and cell division, are not in the model, so their deletion cannot be predicted either way.
- **Complete knockouts, not point mutations.** The effect of a specific base change is not modelled.
- **Steady-state growth.** Flux balance analysis describes balanced exponential growth; lag phases, stationary phase and changes over time are not simulated.
- **Optimal growth assumption.** The model assumes the cell grows as fast as its network allows, which overestimates fast growth on sugars (see [Validation](#validation)).
- **Custom DNA** is scored for expression, but a part that is not linked to a metabolic reaction does not change growth.

---

## Roadmap

- **Enzyme-constrained model.** Add a protein budget so overflow metabolism (acetate secretion on fast sugars) is predicted rather than missed.
- **Temperature validation.** Check the heat response against an independent temperature–growth dataset.
- **Validation on minimal medium.** Compare knockout predictions with a glucose minimal-medium essentiality screen, matching the conditions users simulate most.
- **More strains.** Represent common laboratory strains such as BW25113 as preset sets of gene differences from MG1655.

---

## Team

| Member | Focus |
| --- | --- |
| **Arpit Makkar** | Data layer, API, flux balance analysis, user interface |
| **Keshav Sharma** | AI expression prediction (HyenaDNA, expression model, RBS calculator), validation |
| **Jorogon A** | Simulation pipeline |
| **Nash Murray** | Simulation pipeline |