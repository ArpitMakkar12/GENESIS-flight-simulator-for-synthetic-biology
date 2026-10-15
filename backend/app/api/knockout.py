"""Gene search for the knockout picker on the Simulate page.

Only genes in the metabolic model (iML1515, about 1,500 of the genome's
4,651) can be knocked out, because a knockout works by switching off the
reactions a gene's enzyme runs. So this searches the gene table but keeps
only model genes, and adds each gene's record from the essential-gene check.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.simulate import get_runner
from app.database import get_db
from app.models.gene import Gene
from app.services.essentiality_record import record_for

router = APIRouter()


@router.get("/knockout/genes")
async def search_knockout_genes(
    search: Optional[str] = Query(None, max_length=50, description="Gene name, locus tag or product, e.g. 'pfk', 'b0903', 'kinase'"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Model genes matching a search, each with its essentiality record.

    Returns {items, total}: total is how many model genes match, so the
    picker can say "showing 10 of 37".
    """
    model_genes = get_runner().fba_solver.gene_ids()
    condition = Gene.locus_tag.in_(model_genes)
    # Best matches first: "eno" should find the gene eno before every
    # product that merely contains the letters (adENOsine, ...)
    rank = None
    if search and search.strip():
        q = search.strip()
        pattern = f"%{q}%"
        condition = condition & or_(
            Gene.name.ilike(pattern),
            Gene.locus_tag.ilike(pattern),
            Gene.product.ilike(pattern),
        )
        rank = case(
            (func.lower(Gene.name) == q.lower(), 0),       # exact gene name
            (func.lower(Gene.locus_tag) == q.lower(), 0),  # exact locus tag
            (Gene.name.ilike(f"{q}%"), 1),                 # name starts with it
            (Gene.locus_tag.ilike(f"{q}%"), 2),            # locus tag starts with it
            (Gene.name.ilike(pattern), 3),                 # name contains it
            else_=4,                                       # only the product matches
        )

    total = (await db.execute(select(func.count(Gene.id)).where(condition))).scalar_one()
    rows = (await db.execute(
        select(Gene.locus_tag, Gene.name, Gene.product)
        .where(condition)
        .order_by(*([rank] if rank is not None else []), Gene.name, Gene.locus_tag)
        .limit(limit)
    )).all()

    return {
        "items": [
            {
                "locus_tag": tag,
                "name": name or None,
                "product": product or None,
                "record": record_for(tag),
            }
            for tag, name, product in rows
        ],
        "total": total,
    }