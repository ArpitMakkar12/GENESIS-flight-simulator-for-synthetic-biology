"""Seed genetic_parts table with characterized E. coli genetic parts.

Source: Curated from iGEM Registry + literature
Populates: genetic_parts table

Usage (inside Docker):
    python -m app.data.seed_igem
"""

import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.part import GeneticPart


# Curated characterized parts for E. coli
ECOLI_PARTS = [
    # === PROMOTERS ===
    {"name": "BBa_J23100", "part_type": "promoter", "sequence": "TTGACGGCTAGCTCAGTCCTAGGTACAGTGCTAGC", "description": "Constitutive promoter family member (strongest)", "strength": 1.0, "source": "iGEM Registry", "characterization": {"RPU": 1.0, "reference": True}},
    {"name": "BBa_J23101", "part_type": "promoter", "sequence": "TTTACAGCTAGCTCAGTCCTAGGTATTATGCTAGC", "description": "Constitutive promoter (strong)", "strength": 0.70, "source": "iGEM Registry", "characterization": {"RPU": 0.70}},
    {"name": "BBa_J23106", "part_type": "promoter", "sequence": "TTTACGGCTAGCTCAGTCCTAGGTATAGTGCTAGC", "description": "Constitutive promoter (medium)", "strength": 0.47, "source": "iGEM Registry", "characterization": {"RPU": 0.47}},
    {"name": "BBa_J23114", "part_type": "promoter", "sequence": "TTTATGGCTAGCTCAGTCCTAGGTACAATGCTAGC", "description": "Constitutive promoter (weak)", "strength": 0.10, "source": "iGEM Registry", "characterization": {"RPU": 0.10}},
    {"name": "BBa_J23117", "part_type": "promoter", "sequence": "TTGACAGCTAGCTCAGTCCTAGGGATTGTGCTAGC", "description": "Constitutive promoter (very weak)", "strength": 0.06, "source": "iGEM Registry", "characterization": {"RPU": 0.06}},
    {"name": "BBa_R0010", "part_type": "promoter", "sequence": "CAATACGCAAACCGCCTCTCCCCGCGCGTTGGCCGATTCATTAATGCAGCTGGCACGACAGGTTTCCCGACTGGAAAGCGGGCAGTGAGCGCAACGCAATTAATGTGAGTTAGCTCACTCATTAGGCACCCCAGGCTTTACACTTTATGCTTCCGGCTCGTATGTTGTGTGGAATTGTGAGCGGATAACAATTTCACACA", "description": "lacI-regulated promoter (Plac/ara-1)", "strength": 0.0, "source": "iGEM Registry", "characterization": {"type": "inducible", "inducer": "IPTG", "repressor": "LacI"}},
    {"name": "BBa_R0040", "part_type": "promoter", "sequence": "TCCCTATCAGTGATAGAGATTGACATCCCTATCAGTGATAGAGATACTGAGCAC", "description": "TetR-regulated promoter (pTet)", "strength": 0.0, "source": "iGEM Registry", "characterization": {"type": "inducible", "inducer": "aTc", "repressor": "TetR"}},
    {"name": "BBa_R0011", "part_type": "promoter", "sequence": "AATTGTGAGCGGATAACAATTGACATTGTGAGCGGATAACAAGATACTGAGCACA", "description": "LacI-regulated promoter (pLac)", "strength": 0.0, "source": "iGEM Registry", "characterization": {"type": "inducible", "inducer": "IPTG", "repressor": "LacI"}},
    {"name": "BBa_I0500", "part_type": "promoter", "sequence": None, "description": "Arabinose-inducible promoter (pBAD/AraC)", "strength": 0.0, "source": "iGEM Registry", "characterization": {"type": "inducible", "inducer": "L-arabinose", "repressor": "AraC"}},
    {"name": "Ptrc", "part_type": "promoter", "sequence": "TTGACAATTAATCATCCGGCTCGTATAATGTGTGG", "description": "IPTG-inducible trc promoter (hybrid trp/lac)", "strength": 0.0, "source": "Literature", "characterization": {"type": "inducible", "inducer": "IPTG"}},
    {"name": "PT7", "part_type": "promoter", "sequence": "TAATACGACTCACTATAGGG", "description": "T7 promoter (requires T7 RNAP)", "strength": 0.0, "source": "Literature", "characterization": {"type": "inducible", "requires": "T7 RNA polymerase"}},
    # === RBS ===
    {"name": "BBa_B0034", "part_type": "rbs", "sequence": "AAAGAGGAGAAA", "description": "RBS based on Elowitz repressilator (strong)", "strength": 1.0, "source": "iGEM Registry", "characterization": {"translation_initiation_rate": "high"}},
    {"name": "BBa_B0032", "part_type": "rbs", "sequence": "TCACACAGGAAAG", "description": "Medium-strength RBS", "strength": 0.3, "source": "iGEM Registry", "characterization": {"translation_initiation_rate": "medium"}},
    {"name": "BBa_B0031", "part_type": "rbs", "sequence": "TCACACAGGAAACCTACT", "description": "Weak RBS", "strength": 0.07, "source": "iGEM Registry", "characterization": {"translation_initiation_rate": "low"}},
    {"name": "BBa_B0035", "part_type": "rbs", "sequence": "ATTAAAGAGGAGAAA", "description": "Strong RBS (variant)", "strength": 0.6, "source": "iGEM Registry", "characterization": {"translation_initiation_rate": "high"}},
    # === TERMINATORS ===
    {"name": "BBa_B0015", "part_type": "terminator", "sequence": "CCAGGCATCAAATAAAACGAAAGGCTCAGTCGAAAGACTGGGCCTTTCGTTTTATCTGTTGTTTGTCGGTGAACGCTCTCTACTAGAGTCACACTGGCTCACCTTCGGGTGGGCCTTTCTGCGTTTATA", "description": "Double terminator (B0010 + B0012) — strongest", "strength": 1.0, "source": "iGEM Registry", "characterization": {"efficiency": 0.99, "type": "bidirectional"}},
    {"name": "BBa_B0010", "part_type": "terminator", "sequence": "CCAGGCATCAAATAAAACGAAAGGCTCAGTCGAAAGACTGGGCCTTTCGTTTTATCTGTTGTTTGTCGGTGAACGCTCTC", "description": "T1 from E. coli rrnB", "strength": 0.95, "source": "iGEM Registry", "characterization": {"efficiency": 0.95}},
    {"name": "BBa_B0012", "part_type": "terminator", "sequence": "TCACACTGGCTCACCTTCGGGTGGGCCTTTCTGCGTTTATA", "description": "TE from E. coli rrnB", "strength": 0.9, "source": "iGEM Registry", "characterization": {"efficiency": 0.90}},
    # === REPORTERS (CDS) ===
    {"name": "BBa_E0040", "part_type": "cds", "sequence": None, "description": "GFP (Green Fluorescent Protein) coding sequence", "strength": None, "source": "iGEM Registry", "characterization": {"protein": "GFP", "excitation": 488, "emission": 509}},
    {"name": "BBa_E1010", "part_type": "cds", "sequence": None, "description": "mRFP1 (Red Fluorescent Protein) coding sequence", "strength": None, "source": "iGEM Registry", "characterization": {"protein": "mRFP1", "excitation": 584, "emission": 607}},
    {"name": "BBa_C0012", "part_type": "cds", "sequence": None, "description": "LacI repressor coding sequence", "strength": None, "source": "iGEM Registry", "characterization": {"protein": "LacI", "function": "repressor"}},
    {"name": "BBa_C0040", "part_type": "cds", "sequence": None, "description": "TetR repressor coding sequence", "strength": None, "source": "iGEM Registry", "characterization": {"protein": "TetR", "function": "repressor"}},
    {"name": "BBa_C0080", "part_type": "cds", "sequence": None, "description": "AraC activator coding sequence", "strength": None, "source": "iGEM Registry", "characterization": {"protein": "AraC", "function": "activator"}},
]


def seed_igem() -> None:
    """Insert genetic parts into the database."""
    engine = create_engine(settings.DATABASE_URL_SYNC)

    with Session(engine) as session:
        count = session.execute(text("SELECT COUNT(*) FROM genetic_parts")).scalar()
        if count > 0:
            print(f"Parts table already has {count} rows. Skipping.")
            return

        part_objects = []
        for entry in ECOLI_PARTS:
            part_objects.append(GeneticPart(
                id=uuid.uuid4(),
                name=entry["name"],
                part_type=entry["part_type"],
                sequence=entry.get("sequence") or "N/A",
                source_registry=entry["source"],
                registry_id=entry["name"],
                measured_strength=entry.get("strength"),
                annotations=entry.get("characterization"),
            ))

        session.add_all(part_objects)
        session.commit()

        print(f"Inserted {len(part_objects)} genetic parts")

        # Summary
        types = session.execute(
            text("SELECT part_type, COUNT(*) FROM genetic_parts GROUP BY part_type ORDER BY COUNT(*) DESC")
        ).fetchall()
        print("\nParts by type:")
        for t in types:
            print(f"  {t[1]:>3} {t[0]}")

        # Spot check
        b0034 = session.execute(
            text("SELECT name, part_type, strength FROM genetic_parts WHERE name = 'BBa_B0034'")
        ).fetchone()
        if b0034:
            print(f"\nSpot check: {b0034[0]} | {b0034[1]} | strength={b0034[2]}")


def main():
    print("=" * 60)
    print("SEED: iGEM Genetic Parts (E. coli)")
    print("=" * 60)
    seed_igem()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
