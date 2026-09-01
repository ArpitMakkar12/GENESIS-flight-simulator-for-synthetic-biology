from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.knowledge import GeneResponse, TFResponse, PathwayResponse

router = APIRouter()


@router.get("/genes/{locus_tag}", response_model=GeneResponse)
async def get_gene(
    locus_tag: str,
    db: AsyncSession = Depends(get_db),
):
    """Get gene info by locus tag (e.g., b0001)."""
    # TODO: Query gene from database
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/genes", response_model=list[GeneResponse])
async def search_genes(
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Search genes by name or product."""
    # TODO: Search genes
    return []


@router.get("/tfs", response_model=list[TFResponse])
async def list_transcription_factors(
    condition: Optional[str] = Query(None, description="Filter by active condition"),
    db: AsyncSession = Depends(get_db),
):
    """List transcription factors, optionally filtered by active condition."""
    # TODO: Query TFs
    return []


@router.get("/pathways/{subsystem}", response_model=PathwayResponse)
async def get_pathway(
    subsystem: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all reactions in a metabolic subsystem."""
    # TODO: Query pathway reactions
    raise HTTPException(status_code=501, detail="Not implemented yet")
