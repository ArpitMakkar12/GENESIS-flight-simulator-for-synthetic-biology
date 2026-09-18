from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.construct import Construct, ConstructPart
from app.schemas.construct import ConstructCreate, ConstructResponse

router = APIRouter()


@router.post("/constructs", response_model=ConstructResponse, status_code=201)
async def create_construct(
    construct: ConstructCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a new DNA construct."""
    new_construct = Construct(
        name=construct.name,
        full_sequence=construct.full_sequence,
        metadata_=construct.metadata,
    )
    db.add(new_construct)
    await db.flush()

    # Add parts if provided
    if construct.parts:
        for part_data in construct.parts:
            cp = ConstructPart(
                construct_id=new_construct.id,
                part_id=part_data.part_id,
                position_order=part_data.position_order,
                orientation=part_data.orientation,
            )
            db.add(cp)

    await db.commit()
    await db.refresh(new_construct)
    return new_construct


@router.get("/constructs/{construct_id}", response_model=ConstructResponse)
async def get_construct(
    construct_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a construct by ID."""
    result = await db.execute(
        select(Construct).where(Construct.id == construct_id)
    )
    construct = result.scalar_one_or_none()
    if not construct:
        raise HTTPException(status_code=404, detail=f"Construct '{construct_id}' not found")
    return construct


@router.get("/constructs", response_model=list[ConstructResponse])
async def list_constructs(
    db: AsyncSession = Depends(get_db),
):
    """List all saved constructs."""
    result = await db.execute(
        select(Construct).order_by(Construct.created_at.desc()).limit(50)
    )
    return result.scalars().all()
