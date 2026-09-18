"""Patch subsystem data for reactions from iML1515 JSON model.

The SBML (.xml.gz) from BiGG lacks subsystem annotations.
The JSON model has them. This script downloads the JSON and updates.
"""

import json
import gzip
import uuid
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings

JSON_URL = "https://bigg.ucsd.edu/static/models/iML1515.json"
JSON_PATH = Path("/app/data/models/iML1515.json")


def main():
    print("=" * 60)
    print("PATCH: Reaction subsystem data from iML1515 JSON")
    print("=" * 60)

    # Download JSON model if not present
    if not JSON_PATH.exists():
        print("  Downloading iML1515.json...", end=" ", flush=True)
        resp = httpx.get(JSON_URL, follow_redirects=True, timeout=60)
        resp.raise_for_status()
        JSON_PATH.write_bytes(resp.content)
        print(f"{len(resp.content) / 1e6:.1f} MB")
    else:
        print(f"  iML1515.json already present ({JSON_PATH.stat().st_size / 1e6:.1f} MB)")

    # Parse subsystems from JSON
    with open(JSON_PATH) as f:
        model_data = json.load(f)

    rxn_subsystems = {}
    for rxn in model_data.get("reactions", []):
        rxn_id = rxn.get("id", "")
        subsystem = rxn.get("subsystem", "")
        if rxn_id and subsystem:
            rxn_subsystems[rxn_id] = subsystem

    print(f"  Found {len(rxn_subsystems)} reactions with subsystems in JSON model")

    # Update database
    engine = create_engine(settings.DATABASE_URL_SYNC)
    updated = 0
    with Session(engine) as session:
        for bigg_id, subsystem in rxn_subsystems.items():
            result = session.execute(
                text("UPDATE reactions SET subsystem = :sub WHERE bigg_id = :bid AND (subsystem IS NULL OR subsystem = '')"),
                {"sub": subsystem, "bid": bigg_id},
            )
            updated += result.rowcount
        session.commit()

    print(f"  Updated {updated} reactions with subsystem data")

    # Verify
    with Session(engine) as session:
        count = session.execute(
            text("SELECT COUNT(*) FROM reactions WHERE subsystem IS NOT NULL AND subsystem != ''")
        ).scalar()
        unique = session.execute(
            text("SELECT COUNT(DISTINCT subsystem) FROM reactions WHERE subsystem IS NOT NULL AND subsystem != ''")
        ).scalar()
        print(f"  Verification: {count} reactions have subsystems across {unique} unique pathways")

        # Show top 5
        rows = session.execute(
            text("SELECT subsystem, COUNT(*) AS cnt FROM reactions WHERE subsystem != '' GROUP BY subsystem ORDER BY cnt DESC LIMIT 5")
        ).fetchall()
        print("\n  Top pathways:")
        for sub, cnt in rows:
            print(f"    {cnt:4} reactions — {sub}")

    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
