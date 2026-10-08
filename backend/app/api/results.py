from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.simulation import Simulation

router = APIRouter()


@router.get("/results/{task_id}")
async def get_result(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get simulation results by task ID."""
    result = await db.execute(
        select(Simulation).where(Simulation.id == task_id)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation '{task_id}' not found")

    fba = sim.fba_results or {}
    return {
        "id": str(sim.id),
        "status": sim.status,
        "growth_state": fba.get("growth_state", sim.status),
        "solver_status": fba.get("solver_status"),
        "infeasibility_reason": fba.get("infeasibility_reason"),
        "temperature": sim.temperature,
        "ph": sim.ph,
        "oxygen_level": sim.oxygen_level,
        "carbon_source": sim.carbon_source,
        "nitrogen_source": sim.nitrogen_source,
        "growth_rate": sim.growth_rate,
        "doubling_time": sim.doubling_time,
        "viability_score": sim.viability_score,
        "expression_results": sim.expression_results,
        "fba_results": sim.fba_results,
        "flux_distribution": sim.flux_distribution,
        "model_versions": sim.model_versions,
        "compute_time_ms": sim.compute_time_ms,
        "created_at": sim.created_at.isoformat() if sim.created_at else None,
        "completed_at": sim.completed_at.isoformat() if sim.completed_at else None,
    }


@router.get("/results")
async def list_results(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List recent simulation results."""
    result = await db.execute(
        select(Simulation)
        .order_by(Simulation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sims = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "status": s.status,
            "temperature": s.temperature,
            "ph": s.ph,
            "oxygen_level": s.oxygen_level,
            "carbon_source": s.carbon_source,
            "nitrogen_source": s.nitrogen_source,
            "growth_rate": s.growth_rate,
            "doubling_time": s.doubling_time,
            "viability_score": s.viability_score,
            "compute_time_ms": s.compute_time_ms,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in sims
    ]


@router.delete("/results/{task_id}", status_code=204)
async def delete_result(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a simulation result by ID."""
    result = await db.execute(
        select(Simulation).where(Simulation.id == task_id)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation '{task_id}' not found")
    await db.delete(sim)
    await db.commit()


class BulkDeleteRequest(BaseModel):
    ids: list[UUID] = Field(..., min_length=1, max_length=500)


@router.post("/results/bulk-delete")
async def bulk_delete_results(
    body: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete many simulations in one transaction.

    Returns the ids that were actually removed, so the UI only drops those
    rows. Ids that no longer exist are skipped rather than failing the batch.
    Nothing references simulations, so a plain SQL delete is safe.
    """
    result = await db.execute(
        delete(Simulation)
        .where(Simulation.id.in_(body.ids))
        .returning(Simulation.id)
    )
    deleted = [str(sim_id) for sim_id in result.scalars().all()]
    await db.commit()
    return {"deleted": deleted, "count": len(deleted)}