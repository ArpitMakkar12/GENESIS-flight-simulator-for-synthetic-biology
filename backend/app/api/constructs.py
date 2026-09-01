from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.construct import ConstructCreate, ConstructResponse

router = APIRouter()


@router.post("/constructs", response_model=ConstructResponse, status_code=201)
async def create_construct(
    construct: ConstructCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a new DNA construct."""
    # TODO: Create construct in database
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/constructs/{construct_id}", response_model=ConstructResponse)
async def get_construct(
    construct_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a construct by ID."""
    # TODO: Fetch construct from database
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/constructs", response_model=list[ConstructResponse])
async def list_constructs(
    db: AsyncSession = Depends(get_db),
):
    """List all saved constructs."""
    # TODO: Fetch all constructs
    raise HTTPException(status_code=501, detail="Not implemented yet")
