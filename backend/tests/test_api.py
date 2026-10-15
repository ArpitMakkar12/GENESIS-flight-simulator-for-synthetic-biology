"""End to end through the API: run a simulation, save it, read it back.

Uses the real FastAPI app, database, regulator rules and FBA. Only the AI
expression predictor is replaced by a stub that predicts "no change for
every gene", because the real one needs model files CI does not have.

Every run this test creates is deleted again at the end, so running it
against your Docker database leaves your Results list as it was.
"""

import pytest
from fastapi.testclient import TestClient

from contracts.interfaces import PredictionOutput


class StubPredictor:
    """Stands in for ai.inference.predictor: no gene changes expression."""

    def load_models(self, include_hyenadna=False):
        return {}

    def predict(self, input_data):
        return PredictionOutput(results=[], model_version="test-stub")


@pytest.fixture(scope="module")
def client(runner):
    runner._predictor = StubPredictor()   # set before startup, so warm-up uses it too
    from app.main import app

    created = []
    with TestClient(app) as c:
        c.created = created
        yield c
        for task_id in created:           # leave the database as we found it
            c.delete(f"/api/v1/results/{task_id}")


def simulate(client, **body):
    res = client.post("/api/v1/simulate", json=body)
    if res.status_code == 200:
        client.created.append(res.json()["task_id"])
    return res


def test_reference_run_grows_and_is_saved(client):
    res = simulate(client, temperature=37, ph=7, oxygen_level="aerobic", carbon_source="glucose")
    assert res.status_code == 200, res.text
    run = res.json()
    assert 0.5 < run["growth_rate"] < 1.0
    assert run["solver_status"] == "optimal"
    assert run["knockout"] is None

    saved = client.get(f"/api/v1/results/{run['task_id']}").json()
    assert saved["growth_rate"] == run["growth_rate"]
    assert saved["knockouts"] == []


def test_lethal_knockout_explains_itself(client):
    res = simulate(client, knockout_genes=["b0720"])   # gltA
    assert res.status_code == 200, res.text
    run = res.json()
    assert run["growth_rate"] == 0
    assert run["growth_state"] == "not-viable"
    assert run["infeasibility_reason"].startswith("knockout:")
    assert run["knockout"]["wild_type"]["growth_rate"] > 0.5

    saved = client.get(f"/api/v1/results/{run['task_id']}").json()
    gene = saved["fba_results"]["knockout"]["genes"][0]
    assert gene["locus_tag"] == "b0720"
    assert gene["record"]["agrees"] is True
    assert "pathway_fluxes" in saved["fba_results"]["knockout"]["wild_type"]


def test_partial_knockout_is_compared_with_the_wild_type(client):
    run = simulate(client, knockout_genes=["b2779"]).json()   # eno
    wild_type = run["knockout"]["wild_type"]["growth_rate"]
    assert 0 < run["growth_rate"] < wild_type


def test_unknown_gene_is_refused(client):
    res = simulate(client, knockout_genes=["b9999"])
    assert res.status_code == 422
    assert "b9999" in res.json()["detail"]


def test_knockout_gene_search_only_offers_model_genes(client):
    res = client.get("/api/v1/knockout/genes", params={"search": "b0720"})
    assert res.status_code == 200
    # An empty CI database has no gene table rows; a seeded one finds gltA first
    items = res.json()["items"]
    if items:
        assert items[0]["locus_tag"] == "b0720"