"""Seed the genes table with E. coli K-12 MG1655 genome data.

Source: NCBI GenBank accession NC_000913.3
Method: Biopython Entrez + SeqIO
Populates: genes table (~4,400 rows)

Usage (inside Docker):
    python -m app.data.seed_genome
"""

import uuid
import sys
from io import StringIO

from Bio import Entrez, SeqIO
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models.gene import Gene


# NCBI requires an email
Entrez.email = "biosandbox@example.com"
ACCESSION = "NC_000913.3"  # E. coli K-12 MG1655 complete genome


def calculate_gc(sequence: str) -> float:
    """Calculate GC content of a DNA sequence."""
    if not sequence:
        return 0.0
    seq = sequence.upper()
    gc = seq.count("G") + seq.count("C")
    return round(gc / len(seq), 4)


def download_genome() -> str:
    """Download E. coli K-12 genome from NCBI in GenBank format with full sequences."""
    print(f"Downloading {ACCESSION} from NCBI (full GenBank with sequences)...")
    print("This may take 1-2 minutes for the ~9MB file...")
    handle = Entrez.efetch(
        db="nucleotide",
        id=ACCESSION,
        rettype="gbwithparts",
        retmode="text",
    )
    data = handle.read()
    handle.close()
    print(f"Downloaded {len(data):,} bytes")
    return data


def parse_genes(genbank_text: str) -> list[dict]:
    """Parse GenBank record and extract all gene/CDS features."""
    record = SeqIO.read(StringIO(genbank_text), "genbank")
    genome_seq = str(record.seq)
    print(f"Genome length: {len(genome_seq)} bp")

    genes = {}  # keyed by locus_tag to merge gene + CDS features

    for feature in record.features:
        if feature.type not in ("gene", "CDS"):
            continue

        locus_tag = feature.qualifiers.get("locus_tag", [None])[0]
        if not locus_tag:
            continue

        if locus_tag not in genes:
            genes[locus_tag] = {
                "locus_tag": locus_tag,
                "name": None,
                "product": None,
                "start_pos": int(feature.location.start),
                "end_pos": int(feature.location.end),
                "strand": "+" if feature.location.strand == 1 else "-",
                "dna_sequence": None,
                "protein_sequence": None,
                "cog_category": None,
                "gc_content": None,
                "length_bp": None,
            }

        gene_data = genes[locus_tag]

        # Extract gene name
        gene_name = feature.qualifiers.get("gene", [None])[0]
        if gene_name:
            gene_data["name"] = gene_name

        # Extract product (from CDS features)
        product = feature.qualifiers.get("product", [None])[0]
        if product:
            gene_data["product"] = product

        # Extract protein sequence (from CDS features)
        translation = feature.qualifiers.get("translation", [None])[0]
        if translation:
            gene_data["protein_sequence"] = translation

        # Extract DNA sequence
        try:
            dna_seq = str(feature.location.extract(record.seq))
            gene_data["dna_sequence"] = dna_seq
            gene_data["length_bp"] = len(dna_seq)
            gene_data["gc_content"] = calculate_gc(dna_seq)
        except Exception:
            pass

        # Update positions (CDS may have more precise coordinates)
        gene_data["start_pos"] = int(feature.location.start)
        gene_data["end_pos"] = int(feature.location.end)

    result = list(genes.values())
    print(f"Parsed {len(result)} genes")
    return result


def seed_genes(gene_list: list[dict]) -> None:
    """Insert parsed genes into the database."""
    engine = create_engine(settings.DATABASE_URL_SYNC)

    with Session(engine) as session:
        # Check if already seeded
        count = session.execute(text("SELECT COUNT(*) FROM genes")).scalar()
        if count > 0:
            print(f"Genes table already has {count} rows. Skipping seed.")
            print("To re-seed, run: DELETE FROM genes;")
            return

        # Bulk insert
        gene_objects = []
        for g in gene_list:
            gene_objects.append(Gene(
                id=uuid.uuid4(),
                locus_tag=g["locus_tag"],
                name=g["name"],
                product=g["product"],
                start_pos=g["start_pos"],
                end_pos=g["end_pos"],
                strand=g["strand"],
                dna_sequence=g["dna_sequence"],
                protein_sequence=g["protein_sequence"],
                cog_category=g["cog_category"],
                gc_content=g["gc_content"],
                length_bp=g["length_bp"],
            ))

        session.add_all(gene_objects)
        session.commit()
        print(f"Inserted {len(gene_objects)} genes into database.")

        # Verify with spot checks
        lacZ = session.execute(
            text("SELECT locus_tag, name, product FROM genes WHERE name = 'lacZ'")
        ).fetchone()
        if lacZ:
            print(f"Spot check: {lacZ[0]} | {lacZ[1]} | {lacZ[2]}")

        dnaA = session.execute(
            text("SELECT locus_tag, name, product FROM genes WHERE name = 'dnaA'")
        ).fetchone()
        if dnaA:
            print(f"Spot check: {dnaA[0]} | {dnaA[1]} | {dnaA[2]}")


def main():
    print("=" * 60)
    print("SEED: E. coli K-12 MG1655 Genome")
    print("=" * 60)

    genbank_text = download_genome()
    gene_list = parse_genes(genbank_text)
    seed_genes(gene_list)

    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
