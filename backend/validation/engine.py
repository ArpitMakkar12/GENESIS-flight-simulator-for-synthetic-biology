"""The engine under test — borrowed from the app, never copied.

Validation is only worth anything if it tests the code the app actually
runs. So this module does not define its own model or medium: it calls
the same FBASolver the app uses to load iML1515, and the same
SimulationRunner._get_exchange_constraints the app uses to build a medium.
Change the app, and the next validation run tests the change.
"""

from __future__ import annotations

import cobra

from app.services.fba_solver import FBASolver
from app.services.simulation_runner import (
    MEASURED_AEROBIC_UPTAKE,
    UPTAKE_SOURCES,
    SimulationRunner,
    carbon_uptake_limit,
)


def load_model(model_path: str | None = None) -> cobra.Model:
    """The metabolic model the app uses (iML1515), or another SBML file if given.

    `model_path` exists for development outside Docker — e.g. COBRApy's
    bundled iJO1366 — and should not be used for reported results.
    """
    if model_path:
        model = cobra.io.read_sbml_model(model_path)
        print(f"  Loaded {model.id} from {model_path} (NOT the app's model — development only)")
        return model
    solver = FBASolver()
    solver.load_model()
    return solver.model


def app_medium(carbon_source: str = "glucose", oxygen_level: str = "aerobic") -> dict[str, tuple[float, float]]:
    """The exchange bounds the app applies for a carbon source and oxygen level."""
    return SimulationRunner._get_exchange_constraints(carbon_source, oxygen_level)


def uptake_limit(carbon_source: str, oxygen_level: str = "aerobic") -> tuple[float, str | None]:
    """The app's carbon uptake limit (mmol/gDW/h), and its source if it is a measured rate."""
    measured = oxygen_level == "aerobic" and carbon_source in MEASURED_AEROBIC_UPTAKE
    source = UPTAKE_SOURCES[carbon_source] if measured else None
    return carbon_uptake_limit(carbon_source, oxygen_level), source


def apply_bounds(model: cobra.Model, bounds: dict[str, tuple[float, float]]) -> list[str]:
    """Set reaction bounds on `model` in place; return any IDs the model lacks."""
    missing = []
    for rxn_id, (lb, ub) in bounds.items():
        if rxn_id not in model.reactions:
            missing.append(rxn_id)
            continue
        rxn = model.reactions.get_by_id(rxn_id)
        # Order matters: setting lb above the current ub (or the reverse) raises
        rxn.bounds = (lb, ub)
    return missing