from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
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

    return {
        "id": str(sim.id),
        "status": sim.status,
        "created_at": sim.created_at.isoformat() if sim.created_at else None,
        "completed_at": sim.completed_at.isoformat() if sim.completed_at else None,
        "input_config": sim.input_config,
        "results": sim.results,
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
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in sims
    ]
