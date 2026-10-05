"""Re-apply the hand-curated regulatory edges on top of the PRECISE-1K TRN.

seed_precise.seed_trn() deletes the 38 curated edges from seed_regulondb and
reloads ~10k edges from PRECISE. Where PRECISE gives no direction ("?"), the
curated direction was lost: CRP -> lacZYA became "unknown", so the predictor
skipped CRP and the lactose response ran on LacI alone.

This upgrades "unknown" or missing edges to the curated direction. It never
overrides a direction that PRECISE states.

Run:  docker compose exec backend python -m app.data.apply_curated_regulations
"""
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.data.seed_regulondb import generate_core_regulondb_data


def apply_curated(session: Session) -> dict:
    _, curated = generate_core_regulondb_data()
    stats = {"upgraded": 0, "inserted": 0, "kept": 0, "skipped": 0}

    for edge in curated:
        gene_id = session.execute(
            text("SELECT id FROM genes WHERE lower(name) = lower(:n) LIMIT 1"),
            {"n": edge["gene_name"]},
        ).scalar()
        tf_ids = [row[0] for row in session.execute(
            text("SELECT id FROM transcription_factors WHERE lower(name) = lower(:n)"),
            {"n": edge["tf_name"]},
        )]
        if not gene_id or not tf_ids:
            stats["skipped"] += 1
            continue

        rows = []
        for tf_id in tf_ids:
            rows += session.execute(
                text("SELECT id, regulation_type FROM gene_regulations "
                     "WHERE gene_id = :g AND tf_id = :t"),
                {"g": gene_id, "t": tf_id},
            ).fetchall()

        if not rows:
            session.execute(
                text("INSERT INTO gene_regulations "
                     "(id, gene_id, tf_id, regulation_type, confidence_score, source_db) "
                     "VALUES (:id, :g, :t, :r, :c, 'curated')"),
                {"id": uuid.uuid4(), "g": gene_id, "t": tf_ids[0],
                 "r": edge["regulation_type"], "c": edge["confidence_score"]},
            )
            stats["inserted"] += 1
        elif all(r[1] in ("unknown", None) for r in rows):
            for row_id, _ in rows:
                session.execute(
                    text("UPDATE gene_regulations SET regulation_type = :r, "
                         "source_db = 'curated' WHERE id = :id"),
                    {"r": edge["regulation_type"], "id": row_id},
                )
            stats["upgraded"] += 1
        else:
            stats["kept"] += 1

    session.commit()
    return stats


def main():
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        s = apply_curated(session)
    print(f"curated edges: {s['upgraded']} upgraded from unknown, "
          f"{s['inserted']} added, {s['kept']} already had a direction, "
          f"{s['skipped']} gene/TF not found")


if __name__ == "__main__":
    main()