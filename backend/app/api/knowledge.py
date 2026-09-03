from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.gene import Gene
from app.models.reaction import Reaction
from app.models.regulation import TranscriptionFactor, GeneRegulation
from app.schemas.knowledge import GeneResponse, TFResponse, PathwayResponse, ReactionResponse

router = APIRouter()


@router.get("/genes/{locus_tag}", response_model=GeneResponse)
async def get_gene(
    locus_tag: str,
    db: AsyncSession = Depends(get_db),
):
    """Get gene info by locus tag (e.g., b0344) or gene name (e.g., lacZ)."""
    result = await db.execute(
        select(Gene).where(
            or_(Gene.locus_tag == locus_tag, Gene.name == locus_tag)
        )
    )
    gene = result.scalar_one_or_none()
    if not gene:
        raise HTTPException(status_code=404, detail=f"Gene '{locus_tag}' not found")
    return gene


@router.get("/genes", response_model=list[GeneResponse])
async def search_genes(
    search: Optional[str] = Query(None, description="Search by name, locus_tag, or product"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Search genes by name, locus_tag, or product description."""
    query = select(Gene)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Gene.name.ilike(pattern),
                Gene.locus_tag.ilike(pattern),
                Gene.product.ilike(pattern),
            )
        )

    query = query.order_by(Gene.locus_tag).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/tfs", response_model=list[TFResponse])
async def list_transcription_factors(
    condition: Optional[str] = Query(None, description="Filter by active condition key (e.g., 'oxygen', 'carbon_source')"),
    db: AsyncSession = Depends(get_db),
):
    """List transcription factors, optionally filtered by active condition."""
    query = select(TranscriptionFactor)

    if condition:
        # Filter TFs whose active_conditions JSONB contains the given key
        query = query.where(
            TranscriptionFactor.active_conditions.has_key(condition)
        )

    query = query.order_by(TranscriptionFactor.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/pathways", response_model=list[dict])
async def list_pathways(
    db: AsyncSession = Depends(get_db),
):
    """List all metabolic subsystems with reaction counts."""
    result = await db.execute(
        select(
            Reaction.subsystem,
            func.count(Reaction.id).label("reaction_count"),
        )
        .where(Reaction.subsystem.isnot(None))
        .group_by(Reaction.subsystem)
        .order_by(func.count(Reaction.id).desc())
    )
    rows = result.all()
    return [{"subsystem": r[0], "reaction_count": r[1]} for r in rows]


@router.get("/pathways/{subsystem}", response_model=PathwayResponse)
async def get_pathway(
    subsystem: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all reactions in a metabolic subsystem."""
    result = await db.execute(
        select(Reaction).where(Reaction.subsystem == subsystem)
    )
    reactions = result.scalars().all()
    if not reactions:
        raise HTTPException(status_code=404, detail=f"Subsystem '{subsystem}' not found")
    return PathwayResponse(
        subsystem=subsystem,
        reaction_count=len(reactions),
        reactions=[ReactionResponse.model_validate(r) for r in reactions],
    )
