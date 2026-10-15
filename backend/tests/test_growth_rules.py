"""Rules that label and limit growth. No database, no model.

A change to any of these silently changes every run in the app, so the
exact values are pinned here. If a test fails after a deliberate change,
update the test in the same commit and say why in the message.
"""

import pytest

from app.services.bound_compiler import BoundCompiler
from app.services.simulation_runner import (
    CARBON_UPTAKE_CMMOL,
    REFERENCE_GROWTH_RATE,
    SimulationRunner,
    carbon_uptake_limit,
)

state = SimulationRunner._growth_state


# ── growth_state: judged against the reference growth rate (0.802) ──

@pytest.mark.parametrize("ratio, expected", [
    (1.20, "optimal"),   # faster than reference still counts as optimal
    (0.90, "optimal"),   # boundary: 90% is optimal
    (0.89, "slowed"),
    (0.50, "slowed"),    # boundary: 50% is slowed
    (0.49, "stressed"),
])
def test_growth_state_thresholds(ratio, expected):
    assert state("optimal", REFERENCE_GROWTH_RATE * ratio) == expected


def test_no_growth_is_not_viable():
    assert state("optimal", 0.0) == "not-viable"
    assert state("optimal", 0.009) == "not-viable"   # below 0.01 counts as none
    assert state("infeasible", 0.5) == "not-viable"  # solver failed: never viable


# ── viability: drops only at heat-killing temperatures ──

def test_viability():
    v = SimulationRunner._viability
    assert v(0.0, 37) == 0.0
    assert v(0.8, 37) == 1.0
    assert v(0.8, 46) == 0.7
    assert v(0.8, 48) == 0.4
    assert v(0.8, 50) == 0.1


# ── carbon uptake limits (measured rates, Phase 1) ──

def test_measured_rates_used_with_oxygen():
    assert carbon_uptake_limit("glucose", "aerobic") == 10.0
    assert carbon_uptake_limit("glycerol", "aerobic") == 10.14
    assert carbon_uptake_limit("xylose", "aerobic") == 9.5


def test_without_oxygen_the_old_rule_applies():
    # Measured rates are aerobic only; anaerobic keeps 60 C-mmol
    assert carbon_uptake_limit("glycerol", "anaerobic") == CARBON_UPTAKE_CMMOL / 3
    assert carbon_uptake_limit("glucose", "microaerobic") == CARBON_UPTAKE_CMMOL / 6


def test_unmeasured_sources_fall_back():
    assert carbon_uptake_limit("lactose", "aerobic") == CARBON_UPTAKE_CMMOL / 12
    assert carbon_uptake_limit("arabinose", "aerobic") == CARBON_UPTAKE_CMMOL / 5


def test_exchange_constraints_open_only_the_chosen_carbon():
    bounds = SimulationRunner._get_exchange_constraints("glycerol", "aerobic")
    assert bounds["EX_glyc_e"] == (-10.14, 1000.0)
    assert bounds["EX_glc__D_e"] == (0.0, 1000.0)       # glucose closed
    assert bounds["EX_o2_e"] == (-20.0, 1000.0)
    assert bounds["PFL"] == (0.0, 0.0)                   # PFL off with oxygen
    assert SimulationRunner._get_exchange_constraints("glucose", "anaerobic")["EX_o2_e"] == (0.0, 1000.0)


# ── enzyme activity vs temperature and pH ──

def test_activity_is_full_at_the_optimum():
    assert BoundCompiler.get_activity_factor(37.0, 7.0, 37.0, 7.0) == pytest.approx(1.0)


def test_activity_falls_away_from_the_optimum():
    f = BoundCompiler.get_activity_factor
    assert f(37.0, 7.0, 42.0, 7.0) < 1.0
    assert f(37.0, 7.0, 37.0, 5.5) < 1.0
    # Heat collapse: 50 °C is far worse than the same distance below
    assert f(37.0, 7.0, 50.0, 7.0) < f(37.0, 7.0, 24.0, 7.0)