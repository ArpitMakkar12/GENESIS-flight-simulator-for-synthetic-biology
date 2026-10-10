from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.simulation import Simulation
from app.schemas.simulate import SimulationRequest, SimulationResponse, GeneExpressionOut
from app.services.simulation_runner import SimulationRunner

router = APIRouter()

# Singleton runner — keeps model loaded across requests
_runner: SimulationRunner | None = None


def get_runner() -> SimulationRunner:
    global _runner
    if _runner is None:
        _runner = SimulationRunner()
    return _runner


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(
    request: SimulationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a full BioSandbox simulation pipeline.

    Accepts environmental parameters and returns predicted gene expression,
    metabolic flux, growth rate, and viability. Results are persisted to the
    simulations table for later retrieval via /results.
    """
    runner = get_runner()
    sim_id = uuid4()
    started_at = datetime.now(timezone.utc)

    try:
        result = await runner.run(
            construct_id=request.construct_id,
            raw_sequence=request.raw_sequence,
            temperature=request.temperature,
            ph=request.ph,
            oxygen_level=request.oxygen_level,
            carbon_source=request.carbon_source,
            nitrogen_source=request.nitrogen_source,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    completed_at = datetime.now(timezone.utc)

    # Map expression predictions to response schema
    expression_out = None
    if result.get("expression_predictions"):
        expression_out = [
            GeneExpressionOut(
                gene_id=p["gene_id"],
                relative_expression=p["relative_expression"],
                confidence=p["confidence"],
                prediction_source=p.get("prediction_source"),
                rbs_score=p.get("rbs_score"),
                reference_tpm=p.get("reference_tpm"),
            )
            for p in result["expression_predictions"]
        ]

    # Persist simulation result to database.
    # B1: the `status` column drives the UI badge, so it stores the
    # biological growth_state; the raw solver outcome goes in fba_results.
    # B6: created_at is stamped when the request arrived, not when the row
    # is written, so it can never be later than completed_at.
    model_versions = result.get("model_versions") or {
        "predictor": result.get("model_version", "unknown")
    }
    sim = Simulation(
        id=sim_id,
        name=(request.name or "").strip() or None,
        construct_id=request.construct_id,
        temperature=request.temperature,
        ph=request.ph,
        oxygen_level=request.oxygen_level,
        carbon_source=request.carbon_source,
        nitrogen_source=request.nitrogen_source,
        status=result["growth_state"],
        expression_results=result.get("expression_predictions"),
        expression_all={
            p["gene_id"]: [
                round(p["relative_expression"], 4),
                round(p["confidence"], 3),
                p.get("prediction_source"),
                p.get("reference_tpm"),
            ]
            for p in result.get("expression_all") or []
        } or None,
        fba_results={
            "solver_status": result.get("solver_status"),
            "growth_state": result.get("growth_state"),
            "infeasibility_reason": result.get("infeasibility_reason"),
            "active_pathways": result.get("active_pathways", []),
            "bottlenecks": result.get("bottlenecks", []),
            "flux_summary": result.get("flux_summary", {}),
            "expression_summary": result.get("expression_summary", {}),
            "active_tfs": result.get("active_tfs", []),
            "regulator_state": result.get("regulator_state", {}),
            "tf_state_changes": result.get("tf_state_changes", {}),
        },
        flux_distribution=result.get("flux_distribution"),
        model_versions=model_versions,
        growth_rate=result.get("growth_rate"),
        doubling_time=result.get("doubling_time"),
        viability_score=result.get("viability_score"),
        started_at=started_at,
        completed_at=completed_at,
        created_at=started_at,
        compute_time_ms=result.get("compute_time_ms"),
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)  # load the run_number Postgres just assigned

    return SimulationResponse(
        task_id=sim_id,
        run_number=sim.run_number,
        name=sim.name,
        solver_status=result.get("solver_status"),
        growth_state=result.get("growth_state"),
        status=result.get("solver_status"),
        infeasibility_reason=result.get("infeasibility_reason"),
        growth_rate=result.get("growth_rate"),
        doubling_time=result.get("doubling_time"),
        viability_score=result.get("viability_score"),
        expression_predictions=expression_out,
        expression_summary=result.get("expression_summary"),
        flux_distribution=result.get("flux_distribution"),
        flux_summary=result.get("flux_summary"),
        active_pathways=result.get("active_pathways"),
        active_tfs=result.get("active_tfs"),
        regulator_state=result.get("regulator_state"),
        tf_state_changes=result.get("tf_state_changes"),
        bottlenecks=result.get("bottlenecks"),
        model_versions=model_versions,
        conditions=result.get("conditions"),
        computed_at=completed_at,
        compute_time_ms=result.get("compute_time_ms"),
    )