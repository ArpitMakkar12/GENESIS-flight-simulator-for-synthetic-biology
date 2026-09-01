"""Seed enzyme_kinetics table with E. coli kinetic parameters.

Source: Curated E. coli enzyme kinetics from literature + BRENDA-derived values
       for enzymes present in the iML1515 model.
Populates: enzyme_kinetics table

Usage (inside Docker):
    python -m app.data.seed_brenda
"""

import uuid
import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.kinetics import EnzymeKinetics


# Curated E. coli enzyme kinetics from BRENDA / literature
# These cover the most important central carbon metabolism enzymes
ECOLI_KINETICS = [
    # Glycolysis
    {"ec_number": "2.7.1.1", "substrate": "glucose", "km": 0.04, "kcat": 190.0, "enzyme_name": "Hexokinase / Glucokinase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-45", "ph_range": "6.5-8.5", "specific_activity": 100.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "5.3.1.9", "substrate": "glucose-6-phosphate", "km": 0.3, "kcat": 600.0, "enzyme_name": "Glucose-6-phosphate isomerase", "temp_opt": 37, "ph_opt": 8.0, "temp_range": "25-50", "ph_range": "6.5-9.0", "specific_activity": 500.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "2.7.1.11", "substrate": "fructose-6-phosphate", "km": 0.05, "kcat": 120.0, "enzyme_name": "Phosphofructokinase (PFK)", "temp_opt": 37, "ph_opt": 8.2, "temp_range": "25-45", "ph_range": "7.0-9.0", "specific_activity": 200.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "4.1.2.13", "substrate": "fructose-1,6-bisphosphate", "km": 0.013, "kcat": 20.0, "enzyme_name": "Fructose-bisphosphate aldolase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "20-45", "ph_range": "6.0-8.5", "specific_activity": 15.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "5.3.1.1", "substrate": "dihydroxyacetone phosphate", "km": 0.97, "kcat": 4300.0, "enzyme_name": "Triosephosphate isomerase", "temp_opt": 37, "ph_opt": 7.6, "temp_range": "25-50", "ph_range": "6.5-9.0", "specific_activity": 8000.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "1.2.1.12", "substrate": "glyceraldehyde-3-phosphate", "km": 0.05, "kcat": 170.0, "enzyme_name": "Glyceraldehyde-3-phosphate dehydrogenase (GAPDH)", "temp_opt": 37, "ph_opt": 8.5, "temp_range": "25-50", "ph_range": "7.0-9.5", "specific_activity": 130.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "2.7.2.3", "substrate": "1,3-bisphosphoglycerate", "km": 0.0035, "kcat": 1600.0, "enzyme_name": "Phosphoglycerate kinase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-50", "ph_range": "6.0-8.5", "specific_activity": 1000.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "5.4.2.12", "substrate": "3-phosphoglycerate", "km": 0.5, "kcat": 500.0, "enzyme_name": "Phosphoglycerate mutase", "temp_opt": 37, "ph_opt": 7.0, "temp_range": "25-45", "ph_range": "6.0-8.0", "specific_activity": 300.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "4.2.1.11", "substrate": "2-phosphoglycerate", "km": 0.1, "kcat": 80.0, "enzyme_name": "Enolase", "temp_opt": 37, "ph_opt": 7.0, "temp_range": "25-50", "ph_range": "6.0-8.5", "specific_activity": 60.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "2.7.1.40", "substrate": "phosphoenolpyruvate", "km": 0.31, "kcat": 230.0, "enzyme_name": "Pyruvate kinase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-50", "ph_range": "6.5-8.5", "specific_activity": 350.0, "source_organism": "Escherichia coli K-12"},
    # TCA Cycle
    {"ec_number": "2.3.3.1", "substrate": "oxaloacetate", "km": 0.005, "kcat": 102.0, "enzyme_name": "Citrate synthase", "temp_opt": 37, "ph_opt": 8.0, "temp_range": "25-50", "ph_range": "7.0-9.0", "specific_activity": 80.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "4.2.1.3", "substrate": "citrate", "km": 0.48, "kcat": 18.0, "enzyme_name": "Aconitase", "temp_opt": 37, "ph_opt": 7.4, "temp_range": "25-50", "ph_range": "6.5-8.5", "specific_activity": 15.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "1.1.1.42", "substrate": "isocitrate", "km": 0.008, "kcat": 80.0, "enzyme_name": "Isocitrate dehydrogenase (NADP+)", "temp_opt": 37, "ph_opt": 8.0, "temp_range": "25-50", "ph_range": "7.0-9.0", "specific_activity": 70.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "1.2.4.2", "substrate": "2-oxoglutarate", "km": 0.13, "kcat": 30.0, "enzyme_name": "α-Ketoglutarate dehydrogenase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-45", "ph_range": "6.5-8.5", "specific_activity": 25.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "6.2.1.5", "substrate": "succinate", "km": 0.24, "kcat": 240.0, "enzyme_name": "Succinyl-CoA synthetase", "temp_opt": 37, "ph_opt": 7.4, "temp_range": "25-45", "ph_range": "6.5-8.5", "specific_activity": 180.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "1.3.5.1", "substrate": "succinate", "km": 0.03, "kcat": 50.0, "enzyme_name": "Succinate dehydrogenase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-50", "ph_range": "6.5-8.5", "specific_activity": 40.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "4.2.1.2", "substrate": "fumarate", "km": 0.005, "kcat": 800.0, "enzyme_name": "Fumarase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-50", "ph_range": "6.0-9.0", "specific_activity": 700.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "1.1.1.37", "substrate": "malate", "km": 0.15, "kcat": 560.0, "enzyme_name": "Malate dehydrogenase", "temp_opt": 37, "ph_opt": 8.0, "temp_range": "25-55", "ph_range": "7.0-10.0", "specific_activity": 400.0, "source_organism": "Escherichia coli K-12"},
    # Pentose Phosphate Pathway
    {"ec_number": "1.1.1.49", "substrate": "glucose-6-phosphate", "km": 0.072, "kcat": 180.0, "enzyme_name": "Glucose-6-phosphate dehydrogenase (Zwf)", "temp_opt": 37, "ph_opt": 7.8, "temp_range": "25-50", "ph_range": "7.0-9.0", "specific_activity": 150.0, "source_organism": "Escherichia coli K-12"},
    # Pyruvate metabolism
    {"ec_number": "1.2.4.1", "substrate": "pyruvate", "km": 0.4, "kcat": 50.0, "enzyme_name": "Pyruvate dehydrogenase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-45", "ph_range": "6.5-8.5", "specific_activity": 40.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "1.1.1.28", "substrate": "pyruvate", "km": 0.7, "kcat": 600.0, "enzyme_name": "Lactate dehydrogenase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-50", "ph_range": "6.0-8.5", "specific_activity": 500.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "2.3.1.54", "substrate": "pyruvate", "km": 2.0, "kcat": 800.0, "enzyme_name": "Pyruvate formate-lyase (PFL)", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-42", "ph_range": "6.5-8.5", "specific_activity": 700.0, "source_organism": "Escherichia coli K-12"},
    # Gluconeogenesis
    {"ec_number": "4.1.1.49", "substrate": "oxaloacetate", "km": 0.05, "kcat": 20.0, "enzyme_name": "Phosphoenolpyruvate carboxykinase (PCK)", "temp_opt": 37, "ph_opt": 7.0, "temp_range": "25-45", "ph_range": "6.0-8.0", "specific_activity": 15.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "3.1.3.11", "substrate": "fructose-1,6-bisphosphate", "km": 0.01, "kcat": 25.0, "enzyme_name": "Fructose-1,6-bisphosphatase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-45", "ph_range": "7.0-9.0", "specific_activity": 20.0, "source_organism": "Escherichia coli K-12"},
    # Fermentation
    {"ec_number": "1.1.1.1", "substrate": "acetaldehyde", "km": 0.2, "kcat": 400.0, "enzyme_name": "Alcohol dehydrogenase (AdhE)", "temp_opt": 37, "ph_opt": 7.0, "temp_range": "25-42", "ph_range": "6.0-8.0", "specific_activity": 350.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "2.7.2.1", "substrate": "acetyl-CoA", "km": 0.08, "kcat": 170.0, "enzyme_name": "Acetate kinase (AckA)", "temp_opt": 37, "ph_opt": 7.6, "temp_range": "25-45", "ph_range": "6.5-9.0", "specific_activity": 140.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "2.3.1.8", "substrate": "acetyl-CoA", "km": 0.06, "kcat": 520.0, "enzyme_name": "Phosphotransacetylase (Pta)", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-45", "ph_range": "6.5-9.0", "specific_activity": 400.0, "source_organism": "Escherichia coli K-12"},
    # Amino acid biosynthesis
    {"ec_number": "2.6.1.1", "substrate": "L-aspartate", "km": 3.8, "kcat": 230.0, "enzyme_name": "Aspartate aminotransferase", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-55", "ph_range": "6.5-9.0", "specific_activity": 190.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "2.6.1.11", "substrate": "L-alanine", "km": 1.7, "kcat": 250.0, "enzyme_name": "Alanine aminotransferase", "temp_opt": 37, "ph_opt": 8.0, "temp_range": "25-50", "ph_range": "7.0-9.0", "specific_activity": 200.0, "source_organism": "Escherichia coli K-12"},
    # Oxidative phosphorylation
    {"ec_number": "7.1.1.2", "substrate": "NADH", "km": 0.01, "kcat": 300.0, "enzyme_name": "NADH dehydrogenase I (Nuo complex)", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-45", "ph_range": "6.5-8.5", "specific_activity": 250.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "7.1.1.7", "substrate": "ubiquinol", "km": 0.005, "kcat": 1500.0, "enzyme_name": "Cytochrome bo3 oxidase (Cyo)", "temp_opt": 37, "ph_opt": 7.4, "temp_range": "25-50", "ph_range": "6.5-8.5", "specific_activity": 1200.0, "source_organism": "Escherichia coli K-12"},
    {"ec_number": "7.1.2.2", "substrate": "ADP + Pi", "km": 0.1, "kcat": 200.0, "enzyme_name": "ATP synthase (F1Fo)", "temp_opt": 37, "ph_opt": 7.5, "temp_range": "25-50", "ph_range": "6.5-8.5", "specific_activity": 150.0, "source_organism": "Escherichia coli K-12"},
]


def seed_brenda() -> None:
    """Insert enzyme kinetics into the database."""
    engine = create_engine(settings.DATABASE_URL_SYNC)

    with Session(engine) as session:
        # Check if already seeded
        count = session.execute(text("SELECT COUNT(*) FROM enzyme_kinetics")).scalar()
        if count > 0:
            print(f"Enzyme kinetics table already has {count} rows. Skipping.")
            return

        # Build EC → reaction_id map
        rxn_rows = session.execute(
            text("SELECT id, ec_number FROM reactions WHERE ec_number IS NOT NULL")
        ).fetchall()
        ec_map = {}
        for row in rxn_rows:
            ec = row[1]
            if ec not in ec_map:
                ec_map[ec] = row[0]
        print(f"Found {len(ec_map)} unique EC numbers in reactions table")

        kinetics_objects = []
        matched_ec = 0
        unmatched_ec = 0

        for entry in ECOLI_KINETICS:
            rxn_uuid = ec_map.get(entry["ec_number"])
            if rxn_uuid:
                matched_ec += 1
            else:
                unmatched_ec += 1

            kinetics_objects.append(EnzymeKinetics(
                id=uuid.uuid4(),
                reaction_id=rxn_uuid,
                ec_number=entry["ec_number"],
                substrate=entry["substrate"],
                km_value=entry["km"],
                kcat_value=entry["kcat"],
                specific_activity=entry.get("specific_activity"),
                optimal_temp=float(entry["temp_opt"]),
                optimal_ph=float(entry["ph_opt"]),
                organism_source=entry["source_organism"],
                source_db="BRENDA",
            ))

        session.add_all(kinetics_objects)
        session.commit()

        print(f"Inserted {len(kinetics_objects)} enzyme kinetics entries")
        print(f"EC matched to reactions: {matched_ec} | Unmatched: {unmatched_ec}")

        # Spot checks
        print("\nSpot checks:")
        pfk = session.execute(
            text("SELECT ec_number, substrate, km_value, kcat_value FROM enzyme_kinetics WHERE ec_number = '2.7.1.11'")
        ).fetchone()
        if pfk:
            print(f"  PFK: EC={pfk[0]} | substrate={pfk[1]} | Km={pfk[2]}mM | kcat={pfk[3]}/s")

        cs = session.execute(
            text("SELECT ec_number, substrate, km_value, kcat_value FROM enzyme_kinetics WHERE ec_number = '2.3.3.1'")
        ).fetchone()
        if cs:
            print(f"  Citrate synthase: EC={cs[0]} | substrate={cs[1]} | Km={cs[2]}mM | kcat={cs[3]}/s")


def main():
    print("=" * 60)
    print("SEED: BRENDA Enzyme Kinetics (E. coli)")
    print("=" * 60)
    seed_brenda()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
