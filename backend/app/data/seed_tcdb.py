"""Seed transporters table with E. coli membrane transport proteins.

Source: Curated E. coli transporter data from TCDB classification + EcoCyc
Populates: transporters table

Usage (inside Docker):
    python -m app.data.seed_tcdb
"""

import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.transporter import Transporter


# Curated E. coli transporters covering major substrate transport systems
ECOLI_TRANSPORTERS = [
    # PTS system — glucose and related sugars
    {"gene_name": "ptsG", "transporter_name": "Glucose PTS permease (EIICB)", "tc_family": "4.A.1", "substrate": "glucose", "substrate_chebi_id": "CHEBI:17234", "direction": "import", "mechanism": "PTS (group translocation)", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "manX", "transporter_name": "Mannose PTS permease (EIIAB)", "tc_family": "4.A.6", "substrate": "mannose", "substrate_chebi_id": "CHEBI:28729", "direction": "import", "mechanism": "PTS (group translocation)", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "fruA", "transporter_name": "Fructose PTS permease", "tc_family": "4.A.2", "substrate": "fructose", "substrate_chebi_id": "CHEBI:28645", "direction": "import", "mechanism": "PTS (group translocation)", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "nagE", "transporter_name": "N-acetylglucosamine PTS permease", "tc_family": "4.A.1", "substrate": "N-acetylglucosamine", "substrate_chebi_id": "CHEBI:506227", "direction": "import", "mechanism": "PTS (group translocation)", "atp_cost": 1.0, "is_active": True},
    # ABC transporters — amino acids
    {"gene_name": "hisJ", "transporter_name": "Histidine ABC transporter", "tc_family": "3.A.1.3", "substrate": "L-histidine", "substrate_chebi_id": "CHEBI:57595", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "argT", "transporter_name": "Lysine/arginine/ornithine ABC transporter", "tc_family": "3.A.1.3", "substrate": "L-arginine", "substrate_chebi_id": "CHEBI:32682", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "glnH", "transporter_name": "Glutamine ABC transporter", "tc_family": "3.A.1.3", "substrate": "L-glutamine", "substrate_chebi_id": "CHEBI:58359", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    # ABC transporters — sugars
    {"gene_name": "malE", "transporter_name": "Maltose ABC transporter", "tc_family": "3.A.1.1", "substrate": "maltose", "substrate_chebi_id": "CHEBI:17306", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "rbsB", "transporter_name": "Ribose ABC transporter", "tc_family": "3.A.1.2", "substrate": "D-ribose", "substrate_chebi_id": "CHEBI:47013", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "xylF", "transporter_name": "Xylose ABC transporter", "tc_family": "3.A.1.2", "substrate": "D-xylose", "substrate_chebi_id": "CHEBI:53455", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    # ABC transporters — ions and cofactors
    {"gene_name": "fepA", "transporter_name": "Ferric enterobactin outer membrane receptor", "tc_family": "1.B.14", "substrate": "iron (Fe3+)", "substrate_chebi_id": "CHEBI:29034", "direction": "import", "mechanism": "TonB-dependent receptor", "atp_cost": 0.0, "is_active": True},
    {"gene_name": "znuA", "transporter_name": "Zinc ABC transporter", "tc_family": "3.A.1.15", "substrate": "zinc (Zn2+)", "substrate_chebi_id": "CHEBI:29105", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "pstS", "transporter_name": "Phosphate ABC transporter", "tc_family": "3.A.1.7", "substrate": "phosphate", "substrate_chebi_id": "CHEBI:43474", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    {"gene_name": "modA", "transporter_name": "Molybdate ABC transporter", "tc_family": "3.A.1.8", "substrate": "molybdate", "substrate_chebi_id": "CHEBI:36264", "direction": "import", "mechanism": "ABC transporter", "atp_cost": 1.0, "is_active": True},
    # Symporters / Antiporters
    {"gene_name": "lacY", "transporter_name": "Lactose permease (LacY)", "tc_family": "2.A.1.5", "substrate": "lactose", "substrate_chebi_id": "CHEBI:17716", "direction": "import", "mechanism": "H+ symporter (MFS)", "atp_cost": 0.0, "is_active": True},
    {"gene_name": "galP", "transporter_name": "Galactose:H+ symporter", "tc_family": "2.A.1.1", "substrate": "galactose", "substrate_chebi_id": "CHEBI:28061", "direction": "import", "mechanism": "H+ symporter (MFS)", "atp_cost": 0.0, "is_active": True},
    {"gene_name": "glpF", "transporter_name": "Glycerol facilitator (GlpF)", "tc_family": "1.A.8", "substrate": "glycerol", "substrate_chebi_id": "CHEBI:17754", "direction": "import", "mechanism": "Channel (aquaglyceroporin)", "atp_cost": 0.0, "is_active": False},
    {"gene_name": "araE", "transporter_name": "Arabinose:H+ symporter", "tc_family": "2.A.1.1", "substrate": "L-arabinose", "substrate_chebi_id": "CHEBI:30849", "direction": "import", "mechanism": "H+ symporter (MFS)", "atp_cost": 0.0, "is_active": True},
    {"gene_name": "nhaA", "transporter_name": "Na+/H+ antiporter (NhaA)", "tc_family": "2.A.33", "substrate": "Na+", "substrate_chebi_id": "CHEBI:29101", "direction": "export", "mechanism": "Antiporter", "atp_cost": 0.0, "is_active": True},
    # Efflux / Export
    {"gene_name": "acrB", "transporter_name": "AcrAB-TolC multidrug efflux pump", "tc_family": "2.A.6.2", "substrate": "multiple (antibiotics, bile salts)", "substrate_chebi_id": None, "direction": "export", "mechanism": "RND efflux (H+ antiporter)", "atp_cost": 0.0, "is_active": True},
    {"gene_name": "tolC", "transporter_name": "TolC outer membrane channel", "tc_family": "1.B.17", "substrate": "multiple", "substrate_chebi_id": None, "direction": "export", "mechanism": "Outer membrane channel", "atp_cost": 0.0, "is_active": False},
    # Organic acid transport
    {"gene_name": "actP", "transporter_name": "Acetate/glycolate permease", "tc_family": "2.A.1.1", "substrate": "acetate", "substrate_chebi_id": "CHEBI:30089", "direction": "import", "mechanism": "H+ symporter (MFS)", "atp_cost": 0.0, "is_active": True},
    {"gene_name": "dctA", "transporter_name": "C4-dicarboxylate transporter (DctA)", "tc_family": "2.A.23", "substrate": "succinate", "substrate_chebi_id": "CHEBI:30031", "direction": "import", "mechanism": "H+ symporter (DAACS)", "atp_cost": 0.0, "is_active": True},
    {"gene_name": "focA", "transporter_name": "Formate channel (FocA)", "tc_family": "1.A.16", "substrate": "formate", "substrate_chebi_id": "CHEBI:15740", "direction": "export", "mechanism": "Channel (FNT family)", "atp_cost": 0.0, "is_active": False},
    # Nitrogen transport
    {"gene_name": "amtB", "transporter_name": "Ammonium transporter (AmtB)", "tc_family": "1.A.11", "substrate": "ammonium (NH4+)", "substrate_chebi_id": "CHEBI:28938", "direction": "import", "mechanism": "Channel", "atp_cost": 0.0, "is_active": False},
    {"gene_name": "narK", "transporter_name": "Nitrate/nitrite transporter (NarK)", "tc_family": "2.A.1.8", "substrate": "nitrate", "substrate_chebi_id": "CHEBI:17632", "direction": "import", "mechanism": "MFS antiporter", "atp_cost": 0.0, "is_active": True},
]


def seed_tcdb() -> None:
    """Insert transporters into the database."""
    engine = create_engine(settings.DATABASE_URL_SYNC)

    with Session(engine) as session:
        count = session.execute(text("SELECT COUNT(*) FROM transporters")).scalar()
        if count > 0:
            print(f"Transporters table already has {count} rows. Skipping.")
            return

        # Build gene name -> UUID map
        gene_rows = session.execute(
            text("SELECT id, name FROM genes WHERE name IS NOT NULL")
        ).fetchall()
        gene_map = {row[1]: row[0] for row in gene_rows}
        print(f"Found {len(gene_map)} named genes in database")

        transporter_objects = []
        matched = 0
        unmatched = 0

        for entry in ECOLI_TRANSPORTERS:
            gene_uuid = gene_map.get(entry["gene_name"])
            if gene_uuid:
                matched += 1
            else:
                unmatched += 1
                continue  # Skip if gene not found

            transporter_objects.append(Transporter(
                id=uuid.uuid4(),
                gene_id=gene_uuid,
                tc_family=entry["tc_family"],
                substrate=entry["substrate"],
                substrate_chebi_id=entry.get("substrate_chebi_id"),
                transport_type=entry["mechanism"],
                atp_cost=int(entry["atp_cost"]),
            ))

        session.add_all(transporter_objects)
        session.commit()

        print(f"Inserted {len(transporter_objects)} transporters")
        print(f"Gene matched: {matched} | Unmatched: {unmatched}")

        # Spot checks
        print("\nSpot checks:")
        lacy = session.execute(
            text("""
                SELECT t.tcdb_id, t.substrate, t.transport_type, g.name
                FROM transporters t JOIN genes g ON t.gene_id = g.id
                WHERE g.name = 'lacY'
            """)
        ).fetchone()
        if lacy:
            print(f"  lacY: {lacy[0]} | {lacy[1]} | {lacy[2]}")

        ptsg = session.execute(
            text("""
                SELECT t.tcdb_id, t.substrate, t.transport_type, g.name
                FROM transporters t JOIN genes g ON t.gene_id = g.id
                WHERE g.name = 'ptsG'
            """)
        ).fetchone()
        if ptsg:
            print(f"  ptsG: {ptsg[0]} | {ptsg[1]} | {ptsg[2]}")


def main():
    print("=" * 60)
    print("SEED: TCDB Transporters (E. coli)")
    print("=" * 60)
    seed_tcdb()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
