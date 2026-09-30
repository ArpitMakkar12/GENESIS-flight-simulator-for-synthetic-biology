"""
Idempotent migration: backfill ALL part sequences from iGEM Registry.

Reads authoritative sequences from registry_sequences.json (generated from
the iGEM RSBPML XML API). Each entry has a SHA-256 checksum and
registry-declared length.  The script asserts both before writing.

Run: docker compose exec backend python -m app.data.backfill_cds_sequences
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import select
from app.database import async_session
from app.models.part import GeneticPart

DATA_FILE = Path(__file__).parent / "registry_sequences.json"


async def backfill():
    """Update parts with real sequences from iGEM Registry data file."""
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} not found")
        return

    with open(DATA_FILE) as f:
        registry = json.load(f)

    print(f"Loaded {len(registry)} sequences from {DATA_FILE.name}")

    async with async_session() as session:
        updated = 0
        skipped = 0

        for part_name, entry in registry.items():
            seq = entry["sequence"].upper().strip()
            expected_len = entry["registry_length"]
            expected_sha = entry["sha256"]

            # Integrity checks
            actual_len = len(seq)
            assert actual_len == expected_len, (
                f"{part_name}: length {actual_len} != declared {expected_len}"
            )

            actual_sha = hashlib.sha256(seq.encode()).hexdigest()
            assert actual_sha == expected_sha, (
                f"{part_name}: SHA-256 mismatch: {actual_sha[:16]}... != {expected_sha[:16]}..."
            )

            assert all(c in "ACGT" for c in seq), (
                f"{part_name}: non-ACGT character found"
            )

            result = await session.execute(
                select(GeneticPart).where(GeneticPart.name == part_name)
            )
            part = result.scalar_one_or_none()
            if not part:
                print(f"  ⚠ {part_name} not in DB, skipping")
                skipped += 1
                continue

            if part.sequence == seq:
                print(f"  · {part_name}: {actual_len} bp — already up to date")
            else:
                part.sequence = seq
                updated += 1
                print(f"  ✓ {part_name}: {actual_len} bp — updated")

        await session.commit()
        print(f"\nDone: {updated} updated, {skipped} skipped, "
              f"{len(registry) - updated - skipped} unchanged")


if __name__ == "__main__":
    asyncio.run(backfill())
