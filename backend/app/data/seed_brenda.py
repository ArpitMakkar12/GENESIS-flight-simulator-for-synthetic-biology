"""Seed the enzyme_kinetics table from the curated BRENDA table.

Source: kinetics_curated.csv next to this file. Every value was read from
BRENDA (https://www.brenda-enzymes.org) on 1 November 2026 with one fixed
rule: E. coli, wild-type enzyme, natural substrate, measured at 25-37 °C,
median of what is left. Optima marked "assay at" in BRENDA are assay
conditions, not optima, so they are left out. The rule and the full audit
trail are in docs/kinetics/.

Each row is attached to the iML1515 reaction named in the CSV (by BiGG ID),
not to "the first reaction with this EC number".

The engine does not use these values (USE_KINETIC_CAPS = False in
bound_compiler.py). They are stored so the data is available and documented.

Usage (inside Docker):
    python -m app.data.seed_brenda            # skip if the table has rows
    python -m app.data.seed_brenda --replace  # delete old rows, then seed
"""

import csv
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.kinetics import EnzymeKinetics

CSV_PATH = Path(__file__).with_name("kinetics_curated.csv")
SOURCE = "BRENDA (curated 2026-11-01)"


def _num(value: str) -> float | None:
    """'' -> None, '7.5' -> 7.5"""
    return float(value) if value and value.strip() else None


def seed_brenda(replace: bool = False) -> None:
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        count = session.execute(text("SELECT COUNT(*) FROM enzyme_kinetics")).scalar()
        if count and not replace:
            print(f"Enzyme kinetics table already has {count} rows. Skipping (use --replace).")
            return
        if count:
            session.execute(text("DELETE FROM enzyme_kinetics"))
            print(f"Deleted {count} old rows")

        # BiGG reaction ID -> database UUID
        rxn_ids = dict(session.execute(text("SELECT bigg_id, id FROM reactions")).fetchall())

        rows, missing = [], []
        with open(CSV_PATH, newline="") as f:
            for entry in csv.DictReader(f):
                bigg_id = entry["reaction"]
                if bigg_id not in rxn_ids:
                    missing.append(bigg_id)
                rows.append(EnzymeKinetics(
                    id=uuid.uuid4(),
                    reaction_id=rxn_ids.get(bigg_id),
                    ec_number=entry["ec"],
                    substrate=entry["substrate"],
                    kcat_value=_num(entry["kcat"]),
                    optimal_temp=_num(entry["temp_opt"]),   # None when BRENDA has no real optimum
                    optimal_ph=_num(entry["ph_opt"]),
                    organism_source="Escherichia coli",
                    source_db=SOURCE,
                ))

        session.add_all(rows)
        session.commit()
        print(f"Inserted {len(rows)} curated rows from {CSV_PATH.name}")
        if missing:
            print(f"  Not found in reactions table: {', '.join(missing)}")


def main(replace: bool = False) -> None:
    print("=" * 60)
    print("SEED: enzyme kinetics (curated from BRENDA)")
    print("=" * 60)
    seed_brenda(replace=replace)


if __name__ == "__main__":
    main(replace="--replace" in sys.argv)
