from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.part import GeneticPart

router = APIRouter()


@router.get("/parts")
async def list_parts(
    part_type: Optional[str] = Query(None, description="Filter by type: promoter, rbs, cds, terminator"),
    source: Optional[str] = Query(None, description="Filter by source registry"),
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse the genetic parts library with filters and pagination."""
    query = select(GeneticPart)
    count_query = select(func.count(GeneticPart.id))

    if part_type:
        query = query.where(GeneticPart.part_type == part_type)
        count_query = count_query.where(GeneticPart.part_type == part_type)

    if source:
        query = query.where(GeneticPart.source_registry.ilike(f"%{source}%"))
        count_query = count_query.where(GeneticPart.source_registry.ilike(f"%{source}%"))

    if search:
        pattern = f"%{search}%"
        query = query.where(GeneticPart.name.ilike(pattern))
        count_query = count_query.where(GeneticPart.name.ilike(pattern))

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(GeneticPart.part_type, GeneticPart.name).offset(offset).limit(limit)
    result = await db.execute(query)
    parts = result.scalars().all()

    return {
        "parts": [
            {
                "id": str(p.id),
                "name": p.name,
                "part_type": p.part_type,
                "sequence_length": len(p.sequence) if p.sequence and p.sequence != "N/A" else None,
                "source": p.source_registry,
                "strength": p.measured_strength,
                "annotations": p.annotations,
            }
            for p in parts
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/parts/{part_name}")
async def get_part(
    part_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a genetic part by name."""
    result = await db.execute(
        select(GeneticPart).where(
            or_(GeneticPart.name == part_name, GeneticPart.registry_id == part_name)
        )
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail=f"Part '{part_name}' not found")

    return {
        "id": str(part.id),
        "name": part.name,
        "part_type": part.part_type,
        "sequence": part.sequence,
        "sequence_length": len(part.sequence) if part.sequence and part.sequence != "N/A" else None,
        "source": part.source_registry,
        "registry_id": part.registry_id,
        "strength": part.measured_strength,
        "annotations": part.annotations,
    }
