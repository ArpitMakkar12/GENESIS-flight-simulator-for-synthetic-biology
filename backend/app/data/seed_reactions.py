"""Seed reactions and enzyme_reactions tables from iML1515 metabolic model.

Source: iML1515 SBML model via COBRApy
Populates: reactions table (~2,712 rows) + enzyme_reactions table (gene-reaction links)

Usage (inside Docker):
    python -m app.data.seed_reactions
"""

import uuid
import re

import cobra
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reaction import Reaction, EnzymeReaction
from app.models.gene import Gene


def parse_gpr_genes(gpr_string: str) -> list[str]:
    """Extract individual gene locus tags from a GPR rule string.

    Example: '(b0001 and b0002) or b0003' -> ['b0001', 'b0002', 'b0003']
    """
    if not gpr_string:
        return []
    # Extract all b-numbers (E. coli locus tag format)
    return re.findall(r'b\d{4}', gpr_string)


def seed_reactions() -> None:
    """Load iML1515 and seed reactions + enzyme_reactions."""
    print("Loading iML1515 model...")
    model = cobra.io.read_sbml_model("/app/data/models/iML1515.xml.gz")
    print(f"Model: {model.id} | {len(model.reactions)} reactions | {len(model.genes)} genes")

    engine = create_engine(settings.DATABASE_URL_SYNC)

    with Session(engine) as session:
        # Check if already seeded
        count = session.execute(text("SELECT COUNT(*) FROM reactions")).scalar()
        if count > 0:
            print(f"Reactions table already has {count} rows. Skipping.")
            return

        # Build gene locus_tag -> UUID map from existing genes table
        gene_rows = session.execute(
            text("SELECT id, locus_tag FROM genes")
        ).fetchall()
        gene_map = {row[1]: row[0] for row in gene_rows}
        print(f"Found {len(gene_map)} genes in database for GPR mapping")

        # Insert reactions
        reaction_objects = []
        reaction_id_map = {}  # bigg_id -> UUID for enzyme_reactions

        for rxn in model.reactions:
            rxn_id = uuid.uuid4()
            reaction_id_map[rxn.id] = rxn_id

            # Extract EC number from annotation
            ec_number = None
            if hasattr(rxn, 'annotation') and rxn.annotation:
                ec_list = rxn.annotation.get('ec-code', [])
                if isinstance(ec_list, list) and ec_list:
                    ec_number = ec_list[0]
                elif isinstance(ec_list, str):
                    ec_number = ec_list

            reaction_objects.append(Reaction(
                id=rxn_id,
                bigg_id=rxn.id,
                name=rxn.name,
                subsystem=rxn.subsystem if rxn.subsystem else None,
                reaction_formula=rxn.reaction,
                default_lower_bound=rxn.lower_bound,
                default_upper_bound=rxn.upper_bound,
                is_reversible=rxn.reversibility,
                ec_number=ec_number,
            ))

        session.add_all(reaction_objects)
        session.flush()  # Flush to get IDs for foreign keys
        print(f"Inserted {len(reaction_objects)} reactions")

        # Insert enzyme_reactions (gene-reaction associations)
        enzyme_rxn_objects = []
        matched = 0
        unmatched_genes = set()

        for rxn in model.reactions:
            gpr_string = rxn.gene_reaction_rule
            if not gpr_string:
                continue

            gene_locus_tags = parse_gpr_genes(gpr_string)
            rxn_uuid = reaction_id_map.get(rxn.id)

            for locus_tag in gene_locus_tags:
                gene_uuid = gene_map.get(locus_tag)
                if gene_uuid and rxn_uuid:
                    enzyme_rxn_objects.append(EnzymeReaction(
                        id=uuid.uuid4(),
                        gene_id=gene_uuid,
                        reaction_id=rxn_uuid,
                        gpr_rule=gpr_string,
                    ))
                    matched += 1
                elif locus_tag not in gene_map:
                    unmatched_genes.add(locus_tag)

        session.add_all(enzyme_rxn_objects)
        session.commit()

        print(f"Inserted {len(enzyme_rxn_objects)} enzyme-reaction links")
        print(f"Matched {matched} gene-reaction pairs")
        if unmatched_genes:
            print(f"Warning: {len(unmatched_genes)} genes in iML1515 not found in genome")

        # Spot checks
        print("\nSpot checks:")
        pfk = session.execute(
            text("SELECT bigg_id, name, subsystem, ec_number FROM reactions WHERE bigg_id = 'PFK'")
        ).fetchone()
        if pfk:
            print(f"  PFK: {pfk[1]} | {pfk[2]} | EC:{pfk[3]}")

        biomass = session.execute(
            text("SELECT bigg_id, name FROM reactions WHERE bigg_id LIKE '%BIOMASS%' LIMIT 1")
        ).fetchone()
        if biomass:
            print(f"  Biomass: {biomass[0]} | {biomass[1]}")

        # Count subsystems
        subsystems = session.execute(
            text("SELECT subsystem, COUNT(*) as cnt FROM reactions WHERE subsystem IS NOT NULL GROUP BY subsystem ORDER BY cnt DESC LIMIT 5")
        ).fetchall()
        print(f"\nTop 5 subsystems:")
        for s in subsystems:
            print(f"  {s[1]:>4} reactions | {s[0]}")


def main():
    print("=" * 60)
    print("SEED: iML1515 Reactions + Gene-Reaction Links")
    print("=" * 60)
    seed_reactions()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
