from uuid import uuid4
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.simulate import SimulationRequest, SimulationResponse

router = APIRouter()


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(
    request: SimulationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a full BioSandbox simulation pipeline.

    Accepts a DNA construct + environmental parameters and returns
    predicted gene expression, metabolic flux, and viability.
    """
    # TODO: Implement full simulation pipeline
    # 1. Parse sequence
    # 2. AI expression prediction
    # 3. Compile FBA bounds
    # 4. Run FBA
    # 5. Assemble results
    return SimulationResponse(
        task_id=uuid4(),
        status="pending",
    )
