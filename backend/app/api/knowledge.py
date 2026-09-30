from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.gene import Gene
from app.models.reaction import Reaction
from app.models.regulation import TranscriptionFactor, GeneRegulation
from app.schemas.knowledge import (
    GeneResponse, TFResponse, TFDetailResponse, RegulatedGeneResponse,
    PathwayResponse, ReactionResponse,
)

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
    """List transcription factors with regulated gene counts."""
    # Subquery: count of DISTINCT regulated genes per TF
    reg_count_sub = (
        select(
            GeneRegulation.tf_id,
            func.count(func.distinct(GeneRegulation.gene_id)).label("reg_count"),
        )
        .group_by(GeneRegulation.tf_id)
        .subquery()
    )

    query = (
        select(
            TranscriptionFactor,
            func.coalesce(reg_count_sub.c.reg_count, 0).label("regulated_gene_count"),
        )
        .outerjoin(reg_count_sub, TranscriptionFactor.id == reg_count_sub.c.tf_id)
    )

    if condition:
        query = query.where(
            TranscriptionFactor.active_conditions.has_key(condition)
        )

    query = query.order_by(TranscriptionFactor.name)
    result = await db.execute(query)
    rows = result.all()

    return [
        TFResponse(
            id=tf.id,
            name=tf.name,
            tf_family=tf.tf_family,
            sensing_signal=tf.sensing_signal,
            active_form=tf.active_form,
            active_conditions=tf.active_conditions,
            regulated_gene_count=reg_count,
        )
        for tf, reg_count in rows
    ]


@router.get("/tfs/{tf_name}", response_model=TFDetailResponse)
async def get_transcription_factor(
    tf_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get TF detail with its regulated genes."""
    result = await db.execute(
        select(TranscriptionFactor).where(TranscriptionFactor.name == tf_name)
    )
    tf = result.scalar_one_or_none()
    if not tf:
        raise HTTPException(status_code=404, detail=f"Transcription factor '{tf_name}' not found")

    # Fetch regulated genes with gene info
    reg_result = await db.execute(
        select(GeneRegulation, Gene)
        .join(Gene, GeneRegulation.gene_id == Gene.id)
        .where(GeneRegulation.tf_id == tf.id)
        .order_by(Gene.locus_tag)
    )
    reg_rows = reg_result.all()

    return TFDetailResponse(
        id=tf.id,
        name=tf.name,
        tf_family=tf.tf_family,
        sensing_signal=tf.sensing_signal,
        active_form=tf.active_form,
        active_conditions=tf.active_conditions,
        regulated_gene_count=len(reg_rows),
        regulated_genes=[
            RegulatedGeneResponse(
                gene_locus_tag=gene.locus_tag,
                gene_name=gene.name,
                regulation_type=reg.regulation_type,
                confidence_score=reg.confidence_score,
            )
            for reg, gene in reg_rows
        ],
    )


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
