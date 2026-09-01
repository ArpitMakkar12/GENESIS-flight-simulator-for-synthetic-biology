from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/parts")
async def list_parts(
    part_type: Optional[str] = Query(None, description="Filter by type: promoter, rbs, cds, terminator"),
    source: Optional[str] = Query(None, description="Filter by source: igem, ecocyc, custom"),
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse the genetic parts library."""
    # TODO: Query parts from database with filters
    return {"parts": [], "total": 0, "limit": limit, "offset": offset}
