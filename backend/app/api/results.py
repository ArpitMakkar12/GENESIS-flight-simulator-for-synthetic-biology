from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.simulate import SimulationResponse

router = APIRouter()


@router.get("/results/{task_id}", response_model=SimulationResponse)
async def get_result(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get simulation results by task ID."""
    # TODO: Fetch simulation result
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/results", response_model=list[SimulationResponse])
async def list_results(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List recent simulation results."""
    # TODO: Fetch recent simulations
    return []
