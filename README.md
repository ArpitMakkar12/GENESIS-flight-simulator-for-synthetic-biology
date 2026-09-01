# 🧬 BioSandbox

**AI-Powered E. coli Simulation Platform**

An in-silico biological simulation sandbox that predicts gene expression and metabolic behavior of E. coli under variable environmental conditions.

## Architecture

```
Frontend (Next.js) → API (FastAPI) → AI Engine (HyenaDNA) + FBA (COBRApy) → PostgreSQL + Redis
```

## Quick Start

```bash
# 1. Clone and copy environment config
cp .env.example .env

# 2. Start all services
docker-compose up --build

# 3. Access
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
# API health: http://localhost:8000/health
```

## Project Structure

```
biosandbox/
├── backend/          # FastAPI + SQLAlchemy + COBRApy (Arpit)
├── ai/               # HyenaDNA + Expression models (Keshav)
├── frontend/         # Next.js 14 + TypeScript (Arpit)
├── contracts/        # Shared interface definitions (BOTH)
└── docker-compose.yml
```

## Team

| Member | Owns | Focus |
|--------|------|-------|
| **Arpit** | `backend/`, `frontend/` | Data layer, API, FBA solver, UI |
| **Keshav** | `ai/` | HyenaDNA fine-tuning, expression model, RBS calculator |

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, D3.js, Plotly.js, Cytoscape.js
- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, Celery
- **AI/ML**: PyTorch, HyenaDNA, ONNX Runtime, scikit-learn
- **Simulation**: COBRApy, iML1515 (E. coli GSMM)
- **Database**: PostgreSQL 16, Redis 7
- **Infrastructure**: Docker, Docker Compose

## Data Sources

- [RegulonDB](https://regulondb.ccg.unam.mx/) — Transcription factor regulatory network
- [BRENDA](https://www.brenda-enzymes.org/) — Enzyme kinetic parameters
- [TCDB](https://www.tcdb.org/) — Transporter classification
- [iGEM Registry](https://parts.igem.org/) — Characterized genetic parts
- [iML1515](http://bigg.ucsd.edu/models/iML1515) — E. coli genome-scale metabolic model
