from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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
    metabolic flux, growth rate, and viability.
    """
    runner = get_runner()

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

    # Map expression predictions to response schema
    expression_out = None
    if result.get("expression_predictions"):
        expression_out = [
            GeneExpressionOut(
                gene_id=p["gene_id"],
                relative_expression=p["relative_expression"],
                confidence=p["confidence"],
            )
            for p in result["expression_predictions"]
        ]

    return SimulationResponse(
        task_id=uuid4(),
        status=result["status"],
        growth_rate=result.get("growth_rate"),
        doubling_time=result.get("doubling_time"),
        viability_score=result.get("viability_score"),
        expression_predictions=expression_out,
        active_pathways=result.get("active_pathways"),
        bottlenecks=result.get("bottlenecks"),
        model_versions={"predictor": result.get("model_version", "unknown")},
        computed_at=datetime.now(timezone.utc),
        compute_time_ms=result.get("compute_time_ms"),
    )

