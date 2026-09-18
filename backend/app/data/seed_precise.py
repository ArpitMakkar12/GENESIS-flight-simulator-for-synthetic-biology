"""Seed reference expression (PRECISE-1K) + expanded TRN into the database.

Downloads PRECISE-1K annotation files and:
1. Updates genes.reference_expression_tpm from gene_info.csv
2. Expands gene_regulations from 38 → ~10,000+ using TRN.csv

Usage (inside Docker):
    python -m app.data.seed_precise
"""

import os
import math
from pathlib import Path

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings

BASE_URL = "https://raw.githubusercontent.com/SBRG/precise1k/main/data"
FILES = {
    "gene_info.csv": f"{BASE_URL}/annotation/gene_info.csv",
    "TRN.csv": f"{BASE_URL}/annotation/TRN.csv",
}
DATA_DIR = Path("/app/data/precise")

REF_COL = "p1k_ctrl_log_tpm"  # log2(TPM) under reference condition


def download_files() -> None:
    """Download PRECISE-1K annotation files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        target = DATA_DIR / name
        if target.exists():
            print(f"  {name}: already present ({target.stat().st_size / 1e6:.2f} MB)")
            continue
        print(f"  {name}: downloading...", end=" ", flush=True)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        target.write_bytes(resp.content)
        print(f"{len(resp.content) / 1e6:.2f} MB")


def seed_expression(session: Session) -> None:
    """Update genes.reference_expression_tpm from PRECISE gene_info.csv."""
    # Check if already seeded
    count = session.execute(
        text("SELECT COUNT(*) FROM genes WHERE reference_expression_tpm IS NOT NULL")
    ).scalar()
    if count > 0:
        print(f"\n  Expression already seeded ({count} genes). Skipping.")
        return

    gene_info = pd.read_csv(DATA_DIR / "gene_info.csv")
    print(f"\n  PRECISE gene_info: {len(gene_info)} genes")

    # Build locus_tag -> reference TPM map
    updated = 0
    skipped = 0
    for _, row in gene_info.iterrows():
        locus_tag = str(row["locus_tag"]).strip()
        log_tpm = row.get(REF_COL)

        if pd.isna(log_tpm):
            skipped += 1
            continue

        tpm = 2 ** float(log_tpm)

        result = session.execute(
            text("""
                UPDATE genes
                SET reference_expression_tpm = :tpm,
                    expression_source = 'PRECISE-1K'
                WHERE LOWER(locus_tag) = LOWER(:tag)
            """),
            {"tpm": tpm, "tag": locus_tag},
        )
        if result.rowcount > 0:
            updated += 1

    session.commit()
    print(f"  Updated {updated} genes with reference expression")
    print(f"  Skipped {skipped} (no expression value)")

    # Spot checks
    print("\n  Spot checks:")
    checks = [
        ("b0344", "lacZ", "Should be LOW (glucose media, lactose operon off)"),
        ("b0002", "thrA", "Should be HIGH (amino acid synthesis on minimal media)"),
        ("b3702", "dnaA", "Should be MODERATE (replication initiator)"),
    ]
    for tag, name, why in checks:
        row = session.execute(
            text("SELECT reference_expression_tpm FROM genes WHERE locus_tag = :tag"),
            {"tag": tag},
        ).fetchone()
        if row and row[0]:
            print(f"    {tag} ({name}): {row[0]:,.1f} TPM — {why}")


def seed_trn(session: Session) -> None:
    """Expand gene_regulations from TRN.csv (38 → ~10,000+)."""
    import uuid

    current_count = session.execute(
        text("SELECT COUNT(*) FROM gene_regulations")
    ).scalar()
    if current_count > 100:
        print(f"\n  TRN already expanded ({current_count} regulations). Skipping.")
        return

    # Clear existing small dataset to replace with comprehensive one
    if current_count > 0:
        session.execute(text("DELETE FROM gene_regulations"))
        session.commit()
        print(f"\n  Cleared {current_count} old regulations")

    trn = pd.read_csv(DATA_DIR / "TRN.csv")
    print(f"\n  PRECISE TRN: {trn.columns.tolist()}")
    print(f"  {len(trn)} interactions, {trn['regulator'].nunique()} regulators")

    # Build gene locus_tag -> UUID map
    gene_rows = session.execute(
        text("SELECT id, locus_tag, name FROM genes")
    ).fetchall()
    tag_to_id = {row[1].lower(): row[0] for row in gene_rows}
    name_to_id = {row[2].lower(): row[0] for row in gene_rows if row[2]}

    # Build TF name -> id map from transcription_factors table
    tf_rows = session.execute(
        text("SELECT id, name FROM transcription_factors")
    ).fetchall()
    tf_name_to_id = {row[1].lower(): row[0] for row in tf_rows}

    # First, insert any new TFs not in our table yet
    existing_tf_names = set(tf_name_to_id.keys())
    new_tfs = set()
    for _, row in trn.iterrows():
        reg_name = str(row["regulator"]).strip()
        if reg_name.lower() not in existing_tf_names and reg_name.lower() not in new_tfs:
            new_tfs.add(reg_name.lower())
            tf_id = uuid.uuid4()
            session.execute(
                text("""
                    INSERT INTO transcription_factors (id, name)
                    VALUES (:id, :name)
                    ON CONFLICT DO NOTHING
                """),
                {"id": tf_id, "name": reg_name},
            )
            tf_name_to_id[reg_name.lower()] = tf_id

    if new_tfs:
        session.commit()
        print(f"  Added {len(new_tfs)} new transcription factors")

    # Now insert regulations
    inserted = 0
    unmatched_genes = 0
    unmatched_tfs = 0

    effect_map = {"+": "activator", "-": "repressor", "?": "unknown"}

    for _, row in trn.iterrows():
        reg_name = str(row["regulator"]).strip()
        gene_id_str = str(row.get("gene_id", "")).strip().lower()
        gene_name_str = str(row.get("gene_name", "")).strip().lower() if pd.notna(row.get("gene_name")) else ""
        effect = str(row.get("effect", "?")).strip()

        # Resolve gene
        gene_uuid = tag_to_id.get(gene_id_str) or name_to_id.get(gene_name_str)
        if not gene_uuid:
            unmatched_genes += 1
            continue

        # Resolve TF
        tf_uuid = tf_name_to_id.get(reg_name.lower())
        if not tf_uuid:
            unmatched_tfs += 1
            continue

        reg_type = effect_map.get(effect, "unknown")

        session.execute(
            text("""
                INSERT INTO gene_regulations (id, gene_id, tf_id, regulation_type, confidence_score, source_db)
                VALUES (:id, :gene_id, :tf_id, :reg_type, :conf, :source)
            """),
            {
                "id": uuid.uuid4(),
                "gene_id": gene_uuid,
                "tf_id": tf_uuid,
                "reg_type": reg_type,
                "conf": 0.8,  # published data, good confidence
                "source": "PRECISE-1K",
            },
        )
        inserted += 1

    session.commit()
    print(f"  Inserted {inserted} regulatory interactions")
    print(f"  Unmatched genes: {unmatched_genes}, Unmatched TFs: {unmatched_tfs}")

    # Summary
    total_tfs = session.execute(text("SELECT COUNT(*) FROM transcription_factors")).scalar()
    total_regs = session.execute(text("SELECT COUNT(*) FROM gene_regulations")).scalar()
    print(f"\n  Final: {total_tfs} TFs, {total_regs} regulatory interactions")


def main():
    print("=" * 60)
    print("SEED: PRECISE-1K Expression + TRN")
    print("=" * 60)

    print("\n[1] Downloading PRECISE-1K files")
    download_files()

    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        print("\n[2] Seeding reference expression (gene_info.csv)")
        seed_expression(session)

        print("\n[3] Expanding regulatory network (TRN.csv)")
        seed_trn(session)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
