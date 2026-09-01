"""Seed transcription_factors and gene_regulations tables from RegulonDB.

Source: RegulonDB v12 downloadable datasets
  - network_tf_gene.txt — TF→gene regulatory interactions
Populates: transcription_factors + gene_regulations tables

Usage (inside Docker):
    python -m app.data.seed_regulondb
"""

import uuid
import httpx
from io import StringIO

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.regulation import TranscriptionFactor, GeneRegulation


# RegulonDB dataset URLs
REGULONDB_BASE = "https://regulondb.ccg.unam.mx/menu/download/datasets/files"
NETWORK_TF_GENE_URL = f"{REGULONDB_BASE}/network_tf_gene.txt"


def download_file(url: str) -> str:
    """Download a file from RegulonDB."""
    print(f"Downloading {url}...")
    try:
        response = httpx.get(url, follow_redirects=True, timeout=60)
        response.raise_for_status()
        print(f"Downloaded {len(response.text):,} bytes")
        return response.text
    except Exception as e:
        print(f"Failed to download from RegulonDB: {e}")
        print("Using fallback: generating from known E. coli TF data...")
        return None


def parse_tf_gene_network(content: str) -> tuple[dict, list[dict]]:
    """Parse the RegulonDB network_tf_gene.txt file.

    Returns:
        - dict of TF name -> TF info
        - list of regulation dicts
    """
    tfs = {}
    regulations = []

    for line in content.strip().split("\n"):
        # Skip comments and empty lines
        if line.startswith("#") or line.startswith("//") or not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) < 4:
            continue

        tf_name = parts[0].strip()
        gene_name = parts[1].strip()
        effect = parts[2].strip()  # +, -, +/-, ?
        evidence = parts[3].strip() if len(parts) > 3 else ""

        if not tf_name or not gene_name:
            continue

        # Register TF
        if tf_name not in tfs:
            tfs[tf_name] = {
                "name": tf_name,
                "regulondb_id": None,
                "tf_family": None,
                "sensing_signal": None,
                "active_form": None,
                "active_conditions": None,
            }

        # Map effect to regulation type
        if effect == "+":
            reg_type = "activator"
        elif effect == "-":
            reg_type = "repressor"
        elif effect in ("+/-", "+-"):
            reg_type = "dual"
        else:
            reg_type = "unknown"

        # Map evidence to confidence
        evidence_lower = evidence.lower() if evidence else ""
        if "strong" in evidence_lower or "confirmed" in evidence_lower:
            evidence_level = "strong"
            confidence = 0.9
        elif "weak" in evidence_lower:
            evidence_level = "weak"
            confidence = 0.5
        else:
            evidence_level = "inferred"
            confidence = 0.7

        regulations.append({
            "tf_name": tf_name,
            "gene_name": gene_name,
            "regulation_type": reg_type,
            "confidence_score": confidence,
            "evidence_level": evidence_level,
        })

    return tfs, regulations


def generate_core_regulondb_data() -> tuple[dict, list[dict]]:
    """Generate core RegulonDB data from well-known E. coli regulatory interactions.

    This is a fallback if the download fails, covering the most important TFs.
    """
    # Core transcription factors with known sensing signals
    tfs = {
        "CRP": {"name": "CRP", "regulondb_id": None, "tf_family": "CRP-FNR", "sensing_signal": "cAMP (glucose absence)", "active_form": "CRP-cAMP", "active_conditions": {"carbon_source": ["lactose", "glycerol", "acetate"]}},
        "FNR": {"name": "FNR", "regulondb_id": None, "tf_family": "CRP-FNR", "sensing_signal": "oxygen absence", "active_form": "FNR-[4Fe-4S]", "active_conditions": {"oxygen": ["anaerobic"]}},
        "ArcA": {"name": "ArcA", "regulondb_id": None, "tf_family": "OmpR", "sensing_signal": "anaerobic/microaerobic", "active_form": "ArcA-P", "active_conditions": {"oxygen": ["anaerobic", "microaerobic"]}},
        "NarL": {"name": "NarL", "regulondb_id": None, "tf_family": "LuxR-FixJ", "sensing_signal": "nitrate", "active_form": "NarL-P", "active_conditions": {"nitrogen_source": ["nitrate"]}},
        "Fur": {"name": "Fur", "regulondb_id": None, "tf_family": "Fur", "sensing_signal": "iron (Fe2+)", "active_form": "Fur-Fe2+", "active_conditions": {}},
        "LexA": {"name": "LexA", "regulondb_id": None, "tf_family": "LexA", "sensing_signal": "DNA damage (SOS response)", "active_form": "LexA", "active_conditions": {}},
        "OxyR": {"name": "OxyR", "regulondb_id": None, "tf_family": "LysR", "sensing_signal": "oxidative stress (H2O2)", "active_form": "OxyR-ox", "active_conditions": {}},
        "SoxR": {"name": "SoxR", "regulondb_id": None, "tf_family": "MerR", "sensing_signal": "superoxide", "active_form": "SoxR-ox", "active_conditions": {}},
        "RpoS": {"name": "RpoS", "regulondb_id": None, "tf_family": "Sigma factor", "sensing_signal": "stationary phase / stress", "active_form": "RpoS", "active_conditions": {}},
        "RpoH": {"name": "RpoH", "regulondb_id": None, "tf_family": "Sigma factor", "sensing_signal": "heat shock", "active_form": "RpoH", "active_conditions": {"temperature": [42, 45, 50]}},
        "LacI": {"name": "LacI", "regulondb_id": None, "tf_family": "GalR-LacI", "sensing_signal": "allolactose (lactose presence)", "active_form": "LacI (no inducer)", "active_conditions": {"carbon_source": ["glucose"]}},
        "GalR": {"name": "GalR", "regulondb_id": None, "tf_family": "GalR-LacI", "sensing_signal": "galactose", "active_form": "GalR", "active_conditions": {}},
        "NtrC": {"name": "NtrC", "regulondb_id": None, "tf_family": "NtrC", "sensing_signal": "nitrogen limitation", "active_form": "NtrC-P", "active_conditions": {}},
        "PhoB": {"name": "PhoB", "regulondb_id": None, "tf_family": "OmpR", "sensing_signal": "phosphate limitation", "active_form": "PhoB-P", "active_conditions": {}},
        "Lrp": {"name": "Lrp", "regulondb_id": None, "tf_family": "AsnC-Lrp", "sensing_signal": "leucine", "active_form": "Lrp", "active_conditions": {}},
        "IHF": {"name": "IHF", "regulondb_id": None, "tf_family": "IHF", "sensing_signal": "growth phase", "active_form": "IHF", "active_conditions": {}},
        "Fis": {"name": "Fis", "regulondb_id": None, "tf_family": "Fis", "sensing_signal": "growth phase (exponential)", "active_form": "Fis", "active_conditions": {}},
        "H-NS": {"name": "H-NS", "regulondb_id": None, "tf_family": "H-NS", "sensing_signal": "temperature / osmolarity", "active_form": "H-NS", "active_conditions": {}},
        "FlhDC": {"name": "FlhDC", "regulondb_id": None, "tf_family": "FlhDC", "sensing_signal": "flagellar cascade", "active_form": "FlhD4C2", "active_conditions": {}},
        "NagC": {"name": "NagC", "regulondb_id": None, "tf_family": "ROK", "sensing_signal": "N-acetylglucosamine", "active_form": "NagC", "active_conditions": {}},
    }

    # Key regulatory interactions (curated from RegulonDB knowledge)
    regulations = [
        # CRP activates many catabolic operons when glucose is absent
        {"tf_name": "CRP", "gene_name": "lacZ", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "lacY", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "lacA", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "galE", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "galK", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "malE", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "araB", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "glpF", "regulation_type": "activator", "confidence_score": 0.85, "evidence_level": "strong"},
        {"tf_name": "CRP", "gene_name": "aceB", "regulation_type": "activator", "confidence_score": 0.85, "evidence_level": "strong"},
        # LacI represses lac operon
        {"tf_name": "LacI", "gene_name": "lacZ", "regulation_type": "repressor", "confidence_score": 0.99, "evidence_level": "strong"},
        {"tf_name": "LacI", "gene_name": "lacY", "regulation_type": "repressor", "confidence_score": 0.99, "evidence_level": "strong"},
        {"tf_name": "LacI", "gene_name": "lacA", "regulation_type": "repressor", "confidence_score": 0.99, "evidence_level": "strong"},
        # FNR activates anaerobic genes
        {"tf_name": "FNR", "gene_name": "focA", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "FNR", "gene_name": "pflB", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "FNR", "gene_name": "adhE", "regulation_type": "activator", "confidence_score": 0.85, "evidence_level": "strong"},
        {"tf_name": "FNR", "gene_name": "frdA", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "FNR", "gene_name": "narG", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "FNR", "gene_name": "dmsA", "regulation_type": "activator", "confidence_score": 0.85, "evidence_level": "strong"},
        # FNR represses aerobic genes
        {"tf_name": "FNR", "gene_name": "cyoA", "regulation_type": "repressor", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "FNR", "gene_name": "sdhC", "regulation_type": "repressor", "confidence_score": 0.85, "evidence_level": "strong"},
        {"tf_name": "FNR", "gene_name": "nuoA", "regulation_type": "repressor", "confidence_score": 0.8, "evidence_level": "strong"},
        # ArcA — anaerobic/microaerobic
        {"tf_name": "ArcA", "gene_name": "cyoA", "regulation_type": "repressor", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "ArcA", "gene_name": "sdhC", "regulation_type": "repressor", "confidence_score": 0.85, "evidence_level": "strong"},
        {"tf_name": "ArcA", "gene_name": "icdA", "regulation_type": "repressor", "confidence_score": 0.8, "evidence_level": "strong"},
        {"tf_name": "ArcA", "gene_name": "cydA", "regulation_type": "activator", "confidence_score": 0.85, "evidence_level": "strong"},
        # NarL — nitrate regulation
        {"tf_name": "NarL", "gene_name": "narG", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "NarL", "gene_name": "narK", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "NarL", "gene_name": "frdA", "regulation_type": "repressor", "confidence_score": 0.85, "evidence_level": "strong"},
        # OxyR — oxidative stress
        {"tf_name": "OxyR", "gene_name": "katG", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "OxyR", "gene_name": "ahpC", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "OxyR", "gene_name": "grxA", "regulation_type": "activator", "confidence_score": 0.85, "evidence_level": "strong"},
        # LexA — SOS response
        {"tf_name": "LexA", "gene_name": "recA", "regulation_type": "repressor", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "LexA", "gene_name": "lexA", "regulation_type": "repressor", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "LexA", "gene_name": "uvrA", "regulation_type": "repressor", "confidence_score": 0.9, "evidence_level": "strong"},
        # RpoH — heat shock
        {"tf_name": "RpoH", "gene_name": "groEL", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "RpoH", "gene_name": "groES", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "RpoH", "gene_name": "dnaK", "regulation_type": "activator", "confidence_score": 0.95, "evidence_level": "strong"},
        {"tf_name": "RpoH", "gene_name": "dnaJ", "regulation_type": "activator", "confidence_score": 0.9, "evidence_level": "strong"},
        # Fur — iron regulation
        {"tf_name": "Fur", "gene_name": "fepA", "regulation_type": "repressor", "confidence_score": 0.9, "evidence_level": "strong"},
        {"tf_name": "Fur", "gene_name": "entC", "regulation_type": "repressor", "confidence_score": 0.85, "evidence_level": "strong"},
        {"tf_name": "Fur", "gene_name": "tonB", "regulation_type": "repressor", "confidence_score": 0.85, "evidence_level": "strong"},
    ]

    return tfs, regulations


def seed_regulondb() -> None:
    """Insert TFs and regulations into the database."""
    engine = create_engine(settings.DATABASE_URL_SYNC)

    # Try downloading from RegulonDB first
    content = download_file(NETWORK_TF_GENE_URL)

    if content and len(content) > 1000:
        tfs, regulations = parse_tf_gene_network(content)
        print(f"Parsed from RegulonDB: {len(tfs)} TFs, {len(regulations)} regulations")
    else:
        print("Using curated core dataset...")
        tfs, regulations = generate_core_regulondb_data()
        print(f"Core dataset: {len(tfs)} TFs, {len(regulations)} regulations")

    with Session(engine) as session:
        # Check if already seeded
        count = session.execute(text("SELECT COUNT(*) FROM transcription_factors")).scalar()
        if count > 0:
            print(f"TFs table already has {count} rows. Skipping.")
            return

        # Build gene name -> UUID map
        gene_rows = session.execute(
            text("SELECT id, name FROM genes WHERE name IS NOT NULL")
        ).fetchall()
        gene_map = {row[1]: row[0] for row in gene_rows}
        print(f"Found {len(gene_map)} named genes in database")

        # Insert TFs
        tf_id_map = {}
        tf_objects = []
        for tf_name, tf_info in tfs.items():
            tf_uuid = uuid.uuid4()
            tf_id_map[tf_name] = tf_uuid
            tf_objects.append(TranscriptionFactor(
                id=tf_uuid,
                name=tf_info["name"],
                regulondb_id=tf_info.get("regulondb_id"),
                tf_family=tf_info.get("tf_family"),
                sensing_signal=tf_info.get("sensing_signal"),
                active_form=tf_info.get("active_form"),
                active_conditions=tf_info.get("active_conditions"),
            ))

        session.add_all(tf_objects)
        session.flush()
        print(f"Inserted {len(tf_objects)} transcription factors")

        # Insert regulations
        reg_objects = []
        matched = 0
        unmatched = 0

        for reg in regulations:
            tf_uuid = tf_id_map.get(reg["tf_name"])
            gene_uuid = gene_map.get(reg["gene_name"])

            if tf_uuid and gene_uuid:
                reg_objects.append(GeneRegulation(
                    id=uuid.uuid4(),
                    gene_id=gene_uuid,
                    tf_id=tf_uuid,
                    regulation_type=reg["regulation_type"],
                    confidence_score=reg["confidence_score"],
                    evidence_level=reg["evidence_level"],
                    source_db="RegulonDB",
                ))
                matched += 1
            else:
                unmatched += 1

        session.add_all(reg_objects)
        session.commit()

        print(f"Inserted {len(reg_objects)} regulatory interactions")
        print(f"Matched: {matched} | Unmatched: {unmatched}")

        # Spot checks
        print("\nSpot checks:")
        crp = session.execute(
            text("SELECT name, tf_family, sensing_signal FROM transcription_factors WHERE name = 'CRP'")
        ).fetchone()
        if crp:
            print(f"  CRP: family={crp[1]} | signal={crp[2]}")

        lac_reg = session.execute(
            text("""
                SELECT tf.name, g.name, gr.regulation_type
                FROM gene_regulations gr
                JOIN transcription_factors tf ON gr.tf_id = tf.id
                JOIN genes g ON gr.gene_id = g.id
                WHERE g.name = 'lacZ'
            """)
        ).fetchall()
        for r in lac_reg:
            print(f"  {r[0]} -> lacZ ({r[2]})")


def main():
    print("=" * 60)
    print("SEED: RegulonDB Transcription Factors + Regulations")
    print("=" * 60)
    seed_regulondb()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
