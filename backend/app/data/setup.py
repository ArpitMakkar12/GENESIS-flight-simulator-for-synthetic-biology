"""One command from a fresh clone to a working database.

    docker compose exec backend python -m app.data.setup
    docker compose restart backend        # so the app re-reads the new data

Runs every setup step in the only order that works, then checks the result.
Safe to run again: every step skips what is already done.

Why the order matters. Most seed scripts skip when their table already has
rows, so a step run too early leaves a half-filled table that a later run
will not repair:
  - reactions before genes   -> reactions with no gene links
  - RegulonDB before genes   -> regulators with no target genes
  - BRENDA before reactions  -> kinetics attached to no reaction
  - PRECISE before RegulonDB -> regulators without the condition rules
                                the TF resolver reads
The checks at the end catch exactly these cases. If one fails, start the
database again from empty:  docker compose down -v  (deletes all data,
including saved simulation runs), then  docker compose up -d  and re-run.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time

from sqlalchemy import create_engine, text

from app.config import settings


def count(sql: str) -> int:
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar_one()


def banner(n: int, total: int, title: str) -> None:
    print(f"\n{'━' * 64}\n[{n}/{total}] {title}\n{'━' * 64}", flush=True)


def migrate() -> None:
    """Create or update every table (Alembic migrations)."""
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


def download_metabolic_model() -> None:
    """iML1515 from BiGG into data/models/. seed_reactions reads it but never downloads it."""
    from app.services.fba_solver import FBASolver

    FBASolver().load_model()


def seed_genome() -> None:
    # seed_genome downloads 9 MB before checking the table, so check here first
    if count("SELECT count(*) FROM genes"):
        print("  Genes already loaded, skipping the download.")
        return
    from app.data import seed_genome
    seed_genome.main()


def seed_reactions() -> None:
    from app.data import seed_reactions
    seed_reactions.main()


def patch_subsystems() -> None:
    from app.data import patch_subsystems
    patch_subsystems.main()


def seed_regulondb() -> None:
    from app.data import seed_regulondb
    seed_regulondb.main()


def seed_small_tables() -> None:
    """Enzyme kinetics, transporters and genetic parts: small built-in lists."""
    from app.data import seed_brenda, seed_igem, seed_tcdb
    seed_brenda.main()
    seed_tcdb.main()
    seed_igem.main()


def backfill_part_sequences() -> None:
    from app.data.backfill_cds_sequences import backfill
    asyncio.run(backfill())


def seed_precise() -> None:
    """Measured expression and the full regulatory network (also applies the curated edges)."""
    from app.data import seed_precise
    seed_precise.main()


STEPS = [
    ("Database tables (migrations)", migrate),
    ("Metabolic model iML1515 (download)", download_metabolic_model),
    ("Genes: E. coli K-12 MG1655 genome from NCBI (1-2 min)", seed_genome),
    ("Reactions and gene-reaction links from iML1515", seed_reactions),
    ("Pathway names for reactions", patch_subsystems),
    ("Regulators: RegulonDB core network", seed_regulondb),
    ("Enzyme kinetics, transporters, genetic parts", seed_small_tables),
    ("Full DNA sequences for coding parts", backfill_part_sequences),
    ("PRECISE-1K: measured expression and regulatory network", seed_precise),
]


# ── Checks: (description, SQL returning one number, smallest acceptable value) ──
CHECKS = [
    ("genes", "SELECT count(*) FROM genes", 4000),
    ("genes with measured expression", "SELECT count(*) FROM genes WHERE reference_expression_tpm IS NOT NULL", 1000),
    ("reactions", "SELECT count(*) FROM reactions", 2700),
    ("gene-reaction links", "SELECT count(*) FROM enzyme_reactions", 4000),
    ("reactions with a pathway name", "SELECT count(*) FROM reactions WHERE subsystem IS NOT NULL AND subsystem <> ''", 2000),
    ("regulators", "SELECT count(*) FROM transcription_factors", 100),
    ("regulators with condition rules", "SELECT count(*) FROM transcription_factors WHERE active_conditions IS NOT NULL", 1),
    ("regulatory edges", "SELECT count(*) FROM gene_regulations", 5000),
    ("kinetics linked to a reaction", "SELECT count(*) FROM enzyme_kinetics WHERE reaction_id IS NOT NULL", 1),
    ("transporters", "SELECT count(*) FROM transporters", 1),
    ("genetic parts", "SELECT count(*) FROM genetic_parts", 20),
]


def check() -> bool:
    engine = create_engine(settings.DATABASE_URL_SYNC)
    ok = True
    with engine.connect() as conn:
        for label, sql, minimum in CHECKS:
            value = conn.execute(text(sql)).scalar_one()
            passed = value >= minimum
            ok &= passed
            print(f"  {'✓' if passed else '✗'} {label:34} {value:>7,}   (need ≥ {minimum:,})")
        missing = conn.execute(text(
            "SELECT name FROM genetic_parts WHERE sequence IS NULL OR sequence = 'N/A' ORDER BY name"
        )).scalars().all()
    if missing:
        print(f"  · parts still without a sequence (shown as N/A in the Library): {', '.join(missing)}")
    return ok


def main() -> None:
    started = time.time()
    for n, (title, step) in enumerate(STEPS, start=1):
        banner(n, len(STEPS) + 1, title)
        try:
            step()
        except Exception as e:  # stop: every later step depends on the earlier ones
            print(f"\n✗ Step {n} failed: {type(e).__name__}: {e}")
            print("  Fix the cause (often a network problem; see the README), then run this again."
                  " Finished steps are skipped.")
            sys.exit(1)

    banner(len(STEPS) + 1, len(STEPS) + 1, "Checking the result")
    if not check():
        print("\n✗ Some tables are short. If a step ran out of order earlier, the table stays half-filled:")
        print("  reset with  docker compose down -v  (deletes all data), then  docker compose up -d  and run this again.")
        sys.exit(1)

    print(f"\n✓ Database ready in {time.time() - started:.0f} s.")
    print("  Next:  docker compose restart backend   (the app reads this data once, at startup)")
    print("  Then open http://localhost:3000")


if __name__ == "__main__":
    main()