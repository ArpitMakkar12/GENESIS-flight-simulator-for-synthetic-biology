# GENESIS — Project Progress Log

> **Last Updated**: 2026-09-02 | **Updated By**: Arpit

This file tracks the complete progress, decisions, and context for all team members. **Update this file at the end of every work session before pushing.**

---

## Team Ownership

| Member | Owns | Branch Pattern |
|--------|------|----------------|
| **Arpit** | `backend/`, `frontend/`, `docker-compose.yml`, `docs/` | `arpit/feature-name` |
| **Keshav** | `ai/`, `backend/app/services/rbs_calculator.py` | `keshav/feature-name` |
| **Shared** | `contracts/interfaces.py`, `tests/`, `README.md`, `docs/logs.md` | PR to `main` |

---

## Progress Timeline

### 📅 2026-09-01 — Foundation + Data Layer (Arpit)

#### Phase 1: Foundation ✅ COMPLETE
- [x] Monorepo structure created (72 files)
- [x] Docker Compose — PostgreSQL 16, Redis 7, FastAPI backend, Next.js frontend
- [x] Git repo initialized + pushed to GitHub
- [x] Alembic database migrations — all 11 tables created
- [x] GitHub Actions CI/CD pipeline (`.github/workflows/ci.yml`)
- [x] iML1515 metabolic model verified via COBRApy (2,712 reactions, growth rate = 0.877 hr⁻¹)
- [x] Frontend shell — 5 pages: Home, Simulate, Parts, Results, Knowledge

#### Phase 2: Data Seeding ✅ COMPLETE (Steps 1-6)
All seed scripts are in `backend/app/data/`:

| Seed Script | Table | Rows | Source |
|-------------|-------|------|--------|
| `seed_genome.py` | genes | 4,651 | NCBI GenBank NC_000913.3 |
| `seed_reactions.py` | reactions + enzyme_reactions | 2,712 + 4,754 | iML1515 via COBRApy |
| `seed_regulondb.py` | transcription_factors + gene_regulations | 20 + 38 | RegulonDB (curated core set) |
| `seed_brenda.py` | enzyme_kinetics | 32 | BRENDA (curated E. coli enzymes) |
| `seed_tcdb.py` | transporters | 26 | TCDB classification |
| `seed_igem.py` | genetic_parts | 23 | iGEM Registry |

**Total: 12,256 rows of real biological data in PostgreSQL.**

#### Phase 2: Remaining
- [ ] Step 7: Implement Knowledge API endpoints (actual DB queries replacing stubs)
- [ ] Step 8: Connect Parts Library UI to API

---

## Architecture Decisions Log

| Decision | Choice | Reason |
|----------|--------|--------|
| Organism scope | E. coli K-12 only | Best characterized, most data available, feasible for capstone |
| DB | PostgreSQL only (no Neo4j) | Regulatory graph handled with join tables + recursive CTEs |
| AI model | HyenaDNA (1.6M params) | Open-source, single-nucleotide resolution, runs on CPU |
| Inference | ONNX Runtime on CPU | No GPU needed, <2s target |
| Frontend | Next.js 14 | Server components, app router, TypeScript |
| Backend | FastAPI | Async, auto-docs, Pydantic validation |
| Package name | `cobra` not `cobrapy` | PyPI package name is `cobra` |
| `reaction_formula` column | Changed from `VARCHAR(1000)` to `TEXT` | Some iML1515 formulas exceed 1000 chars |
| Docker Compose version key | Removed `version: '3.8'` | Obsolete in modern Docker Compose |

---

## Database Schema Summary

```
genes (4,651 rows)
├── locus_tag, name, product, start_pos, end_pos, strand
├── dna_sequence, protein_sequence, gc_content, length_bp
│
├── → enzyme_reactions (4,754 rows) → reactions (2,712 rows)
│     └── bigg_id, name, subsystem, reaction_formula, ec_number, bounds
│
├── → gene_regulations (38 rows) ← transcription_factors (20 rows)
│     └── regulation_type (activator/repressor), confidence_score
│
├── → transporters (26 rows)
│     └── tc_family, substrate, transport_type, atp_cost
│
├── enzyme_kinetics (32 rows) → reactions
│     └── ec_number, substrate, km_value, kcat_value, optimal_temp/ph
│
├── genetic_parts (23 rows)
│     └── name, part_type, sequence, measured_strength
│
├── constructs → construct_parts
└── simulations
```

---

## How to Set Up (New Team Member)

```bash
# 1. Clone
git clone https://github.com/ArpitMakkar12/GENESIS-flight-simulator-for-synthetic-biology.git
cd GENESIS-flight-simulator-for-synthetic-biology

# 2. Start Docker (make sure Docker Desktop is running)
docker compose up --build -d

# 3. Run migrations
docker compose exec backend alembic upgrade head

# 4. Seed data (run in order)
docker compose exec backend python -m app.data.seed_genome
docker compose exec backend python -m app.data.seed_reactions
docker compose exec backend python -m app.data.seed_regulondb
docker compose exec backend python -m app.data.seed_brenda
docker compose exec backend python -m app.data.seed_tcdb
docker compose exec backend python -m app.data.seed_igem

# 5. Verify
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
# DB check: docker compose exec db psql -U biosandbox -c "\dt"
```

---

## Daily Workflow

```
MORNING:
  git pull origin main

DURING THE DAY:
  git add .
  git commit -m "descriptive message"

END OF DAY:
  # Update this log file with what you did today!
  git pull origin main
  git push origin main
```

---

## Keshav — Your Starting Point

Your workspace is the `ai/` folder. Everything is stubbed out for you:

```
ai/
├── models/
│   ├── hyenadna_wrapper.py    ← Wrap HyenaDNA model here
│   ├── expression_fusion.py   ← Expression prediction model
│   └── model_registry.py      ← Load/version models
├── inference/
│   ├── predictor.py           ← Implements ExpressionPredictor from contracts/interfaces.py
│   └── env_conditioner.py     ← Convert environment params to model features
└── training/                  ← Your training scripts
```

**The contract** you must implement is in `contracts/interfaces.py`:
- `PredictionInput` → `ExpressionPredictor.predict()` → `PredictionOutput`
- Arpit's backend calls your predictor — one-directional dependency

**Do NOT modify** files outside `ai/` and `backend/app/services/rbs_calculator.py`.

---

## Known Issues / Gotchas

1. **Docker `version` warning** — Ignore the "attribute `version` is obsolete" warning, it's cosmetic
2. **RegulonDB SSL** — Direct download fails due to SSL cert issue; using curated fallback dataset (20 core TFs)
3. **BRENDA bulk download** — Requires registration; using curated 32-enzyme dataset covering central metabolism
4. **BiGG redirect** — `cobra.io.load_model('iML1515')` fails due to HTTP→HTTPS redirect; we download the SBML file directly
5. **`libexpat1`** — Must be installed in backend Docker image for COBRApy/libsbml to work
