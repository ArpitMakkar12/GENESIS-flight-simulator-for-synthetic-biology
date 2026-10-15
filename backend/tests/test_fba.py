"""The metabolic engine on iML1515: growth, media and gene knockouts.

These solve the real model with the app's own FBASolver and medium, with
no expression bounds, so the numbers are plain iML1515. They guard the
things later phases rely on:
  - wild-type growth on the reference medium
  - the measured uptake rates (glycerol must not out-grow glucose again)
  - knockouts: lethal, partial and silent deletions, and that a knockout
    never leaks into the cached model the next run uses

The first run downloads iML1515 (about 1.6 MB) if it is not cached.
The solver reads pathway names from the database, so a database must be
reachable; an empty, migrated one is enough.
"""

import pytest

from app.services.simulation_runner import SimulationRunner


def grow(runner, carbon="glucose", oxygen="aerobic", knockouts=None):
    medium = SimulationRunner._get_exchange_constraints(carbon, oxygen)
    result = runner.fba_solver.solve(bounds=[], exchange_constraints=medium, knockout_genes=knockouts)
    return result.growth_rate if result.status == "optimal" else 0.0


def test_model_is_iml1515(runner):
    model = runner.fba_solver.model
    assert len(model.reactions) == 2712
    assert len(model.genes) == 1516


def test_wild_type_on_glucose(runner):
    # Plain iML1515 on the app's glucose medium; the app's reference (0.802)
    # is lower because expression bounds are applied on top.
    assert grow(runner) == pytest.approx(0.822, abs=0.01)


def test_glycerol_grows_slower_than_glucose(runner):
    # Before the measured uptake rates, glycerol came out fastest (0.861)
    assert grow(runner, "glycerol") < grow(runner, "glucose")


def test_no_oxygen_means_slower_growth(runner):
    assert 0 < grow(runner, oxygen="anaerobic") < grow(runner)


def test_acetate_grows_far_slower_than_glucose(runner):
    assert 0 < grow(runner, "acetate") < 0.5 * grow(runner)


@pytest.mark.parametrize("gene, name, low, high", [
    ("b0720", "gltA", 0.0, 0.0),     # citrate synthase: no route around it on glucose
    ("b2779", "eno", 0.60, 0.72),    # enolase: the serine bypass keeps it alive (~0.665)
    ("b0903", "pflB", 0.80, 0.84),   # pyruvate formate-lyase is off with oxygen anyway
])
def test_single_knockouts(runner, gene, name, low, high):
    growth = grow(runner, knockouts=[gene])
    assert low <= round(growth, 3) <= high, f"Δ{name}: {growth:.3f}"


def test_knockout_does_not_leak_into_the_next_run(runner):
    before = grow(runner)
    grow(runner, knockouts=["b0720"])
    assert grow(runner) == pytest.approx(before)


def test_unknown_gene_is_refused(runner):
    with pytest.raises(KeyError):
        grow(runner, knockouts=["b9999"])


def test_gene_ids_are_locus_tags(runner):
    ids = runner.fba_solver.gene_ids()
    assert {"b0720", "b2779", "b0903"} <= ids
    assert all(g.startswith(("b", "s")) for g in ids)   # s0001 is iML1515's "spontaneous" gene