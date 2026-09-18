"""Download and store the full E. coli K-12 MG1655 genome sequence.

Saves to data/genome/NC_000913.3.fasta for promoter region extraction.

Usage (inside Docker):
    python -m app.data.seed_genome_sequence
"""

from pathlib import Path
from Bio import Entrez, SeqIO

Entrez.email = "biosandbox@example.com"

GENOME_DIR = Path("/app/data/genome")
FASTA_PATH = GENOME_DIR / "NC_000913.3.fasta"
ACCESSION = "NC_000913.3"


def download_genome() -> None:
    """Download E. coli genome and save as FASTA."""
    if FASTA_PATH.exists():
        print(f"  Genome already present ({FASTA_PATH.stat().st_size / 1e6:.1f} MB)")
        return

    GENOME_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  Downloading {ACCESSION} from NCBI...", end=" ", flush=True)
    handle = Entrez.efetch(
        db="nucleotide",
        id=ACCESSION,
        rettype="fasta",
        retmode="text",
    )
    with open(FASTA_PATH, "w") as f:
        f.write(handle.read())
    handle.close()

    # Verify
    record = SeqIO.read(FASTA_PATH, "fasta")
    print(f"{len(record.seq):,} bp")
    print(f"  Saved to {FASTA_PATH}")


def main():
    print("=" * 60)
    print("SEED: E. coli Genome Sequence (FASTA)")
    print("=" * 60)
    download_genome()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
