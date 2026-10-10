from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.gene import Gene
from app.models.reaction import Reaction
from app.models.simulation import Simulation

router = APIRouter()

# Reaction -> (pathway, readable name). The reactions table never changes
# while the app runs, so it is read once and kept in memory.
_reaction_info: dict[str, tuple[str | None, str | None]] | None = None


async def _get_reaction_info(db: AsyncSession) -> dict[str, tuple[str | None, str | None]]:
    global _reaction_info
    if _reaction_info is None:
        rows = (await db.execute(select(Reaction.bigg_id, Reaction.subsystem, Reaction.name))).all()
        _reaction_info = {bigg_id: (subsystem, name) for bigg_id, subsystem, name in rows}
    return _reaction_info


def _pathway_totals(flux_distribution: dict | None, info: dict) -> dict[str, float]:
    """Total |flux| through every pathway, biggest first.

    The solver only keeps a top-15 list in active_pathways, so a pathway
    missing from that list may still carry flux. Summing the saved fluxes
    per pathway gives the full picture, for old runs as well as new ones.
    """
    totals: dict[str, float] = {}
    for rxn_id, flux in (flux_distribution or {}).items():
        subsystem = (info.get(rxn_id) or (None, None))[0]
        if not subsystem or subsystem.strip().lower() in ("unassigned", "none"):
            continue
        totals[subsystem] = totals.get(subsystem, 0.0) + abs(flux)
    return {k: round(v, 3) for k, v in sorted(totals.items(), key=lambda kv: -kv[1])}


def _iso(dt):
    return dt.isoformat() if dt else None


def _summary(s: Simulation) -> dict:
    """Fields shared by the list rows and the detail page."""
    return {
        "id": str(s.id),
        "run_number": s.run_number,
        "name": s.name,
        "status": s.status,
        "temperature": s.temperature,
        "ph": s.ph,
        "oxygen_level": s.oxygen_level,
        "carbon_source": s.carbon_source,
        "nitrogen_source": s.nitrogen_source,
        "growth_rate": s.growth_rate,
        "doubling_time": s.doubling_time,
        "viability_score": s.viability_score,
        "compute_time_ms": s.compute_time_ms,
        "created_at": _iso(s.created_at),
        "completed_at": _iso(s.completed_at),
    }


# NOTE: the fixed paths (/results, /results/filters, /results/bulk-delete) are
# declared before /results/{task_id}; otherwise FastAPI would try to read the
# word "filters" as a simulation id.


@router.get("/results")
async def list_results(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    oxygen: Optional[str] = Query(None, description="Only this oxygen level"),
    carbon: Optional[str] = Query(None, description="Only this carbon source"),
    sort: Literal["created_at", "run_number", "growth_rate", "viability_score"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
):
    """One page of simulations, plus the total so the UI can page through all of them.

    Filtering and sorting happen in the database, so they cover every
    simulation, not just the rows on the current page.
    """
    conditions = []
    if oxygen:
        conditions.append(Simulation.oxygen_level == oxygen)
    if carbon:
        conditions.append(Simulation.carbon_source == carbon)

    column = getattr(Simulation, sort)
    ordering = column.asc() if order == "asc" else column.desc()
    # Runs with no growth value go last either way; run_number breaks ties
    query = (
        select(Simulation)
        .where(*conditions)
        .order_by(ordering.nulls_last(), Simulation.run_number.desc())
        .offset(offset)
        .limit(limit)
    )
    sims = (await db.execute(query)).scalars().all()
    total = (
        await db.execute(select(func.count()).select_from(Simulation).where(*conditions))
    ).scalar_one()

    return {
        "items": [_summary(s) for s in sims],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/results/filters")
async def result_filters(db: AsyncSession = Depends(get_db)):
    """Every oxygen level and carbon source used so far, for the filter dropdowns."""
    oxygen = (await db.execute(select(Simulation.oxygen_level).distinct().order_by(Simulation.oxygen_level))).scalars().all()
    carbon = (await db.execute(select(Simulation.carbon_source).distinct().order_by(Simulation.carbon_source))).scalars().all()
    return {"oxygen_levels": oxygen, "carbon_sources": carbon}


class BulkDeleteRequest(BaseModel):
    ids: list[UUID] = Field(..., min_length=1, max_length=500)


@router.post("/results/bulk-delete")
async def bulk_delete_results(
    body: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete many simulations in one transaction.

    Returns the ids that were actually removed, so the UI only drops those
    rows. Ids that no longer exist are skipped rather than failing the batch.
    Nothing references simulations, so a plain SQL delete is safe.
    """
    result = await db.execute(
        delete(Simulation)
        .where(Simulation.id.in_(body.ids))
        .returning(Simulation.id)
    )
    deleted = [str(sim_id) for sim_id in result.scalars().all()]
    await db.commit()
    return {"deleted": deleted, "count": len(deleted)}


async def _get_or_404(task_id: UUID, db: AsyncSession) -> Simulation:
    sim = (await db.execute(select(Simulation).where(Simulation.id == task_id))).scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation '{task_id}' not found")
    return sim


@router.get("/results/{task_id}")
async def get_result(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get simulation results by task ID."""
    sim = await _get_or_404(task_id, db)
    fba = dict(sim.fba_results or {})
    info = await _get_reaction_info(db)

    # Full pathway totals (not just the top 15) and readable bottleneck names
    fba["pathway_fluxes"] = _pathway_totals(sim.flux_distribution, info)
    fba["bottleneck_names"] = {
        rxn: (info.get(rxn) or (None, None))[1]
        for rxn in fba.get("bottlenecks") or []
        if (info.get(rxn) or (None, None))[1]
    }

    # Gene names (e.g. b0903 -> pflB) next to the locus tags
    expression = [dict(e) for e in (sim.expression_results or [])]
    tags = [e.get("gene_id") for e in expression if e.get("gene_id")]
    if tags:
        names = dict((await db.execute(select(Gene.locus_tag, Gene.name).where(Gene.locus_tag.in_(tags)))).all())
        for e in expression:
            e.setdefault("gene_name", names.get(e.get("gene_id")) or None)  # "" -> None

    return {
        **_summary(sim),
        "growth_state": fba.get("growth_state", sim.status),
        "solver_status": fba.get("solver_status"),
        "infeasibility_reason": fba.get("infeasibility_reason"),
        "expression_results": expression or sim.expression_results,
        "fba_results": fba,
        "flux_distribution": sim.flux_distribution,
        "model_versions": sim.model_versions,
    }


class RenameRequest(BaseModel):
    # Empty string or null clears the name (the UI then shows the auto title)
    name: Optional[str] = Field(default=None, max_length=120)


@router.patch("/results/{task_id}")
async def rename_result(
    task_id: UUID,
    body: RenameRequest,
    db: AsyncSession = Depends(get_db),
):
    """Give a simulation a name, or clear it."""
    sim = await _get_or_404(task_id, db)
    sim.name = (body.name or "").strip() or None
    await db.commit()
    return {"id": str(sim.id), "run_number": sim.run_number, "name": sim.name}


@router.delete("/results/{task_id}", status_code=204)
async def delete_result(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a simulation result by ID."""
    sim = await _get_or_404(task_id, db)
    await db.delete(sim)
    await db.commit()