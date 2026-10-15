"""Shared setup for the backend tests.

Run from backend/:   python -m pytest
In Docker:           docker compose exec backend python -m pytest

Three kinds of test live here:
  - pure rules (growth labels, uptake limits, regulator rules): no database
  - FBA on iML1515: needs the database only for pathway names (empty is fine)
  - one end-to-end API test: needs a migrated database

The AI expression model is NOT used. It needs large model files that CI
does not have, and these tests check the metabolic engine and the API,
not the predictor. test_api.py swaps in a stub that predicts "no change".
"""

import sys
from pathlib import Path

import pytest

# contracts/ and ai/ sit next to backend/ in the repo, but inside backend/
# (/app) in Docker. Put whichever folder holds them on the import path.
_here = Path(__file__).resolve()
for folder in (_here.parents[1], _here.parents[2]):
    if (folder / "contracts").is_dir() and str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


@pytest.fixture(scope="session")
def runner():
    """The app's own SimulationRunner, with iML1515 loaded once for all tests."""
    from app.api.simulate import get_runner

    r = get_runner()
    r.fba_solver.load_model()
    return r


@pytest.fixture(scope="session")
def glucose_medium():
    """The exchange bounds the app uses for glucose, aerobic."""
    from app.services.simulation_runner import SimulationRunner

    return SimulationRunner._get_exchange_constraints("glucose", "aerobic")