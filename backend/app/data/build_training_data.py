"""Build the training dataset: promoter sequence -> expression level.

Run inside the backend container:
    docker compose exec backend python -m app.data.build_training_data

Owned by: Keshav

WHAT THIS MAKES
---------------
A CSV where each row is one gene:

    locus_tag, gene_name, strand, promoter (300bp), cds_start (100bp),
    reference_tpm, log2_tpm, in_iml1515

That is the textbook the model learns from. Show it enough rows and it
learns to predict the expression column from the promoter column.

WHERE THE DATA COMES FROM
-------------------------
    expression  -> genes.reference_expression_tpm (seeded from PRECISE-1K)
    promoter    -> cut out of the genome FASTA using each gene's coordinates

THE STRAND PROBLEM
------------------
DNA has two strands and genes sit on either one. For a gene on the '+'
strand, the 300bp upstream is immediately BEFORE its start position. For
a gene on the '-' strand the gene is read backwards, so its upstream
region is AFTER its end position in the file, and must be reverse
complemented.

Get this wrong and roughly half the dataset is silently wrong. So this
script validates itself: it re-extracts each gene's own coding sequence
from the genome and compares it against what the database stores. If
those agree, the coordinate and strand handling is correct.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import settings

GENOME_PATH = Path("/app/data/genome/NC_000913.3.fasta")
OUTPUT_PATH = Path("/app/data/training/promoter_expression.csv")

UPSTREAM_BP = 300      # promoter region, per the contract
CDS_HEAD_BP = 100      # first bit of the gene itself, useful context

COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def reverse_complement(seq: str) -> str:
    """Flip a DNA sequence to read it from the other strand."""
    return seq.translate(COMPLEMENT)[::-1]


def load_genome() -> str:
    """Read the FASTA file into one long string of letters."""
    if not GENOME_PATH.exists():
        raise FileNotFoundError(
            f"No genome at {GENOME_PATH}. Run:\n"
            "  docker compose exec backend python -m app.data.seed_genome_sequence"
        )
    lines = GENOME_PATH.read_text().splitlines()
    return "".join(l.strip() for l in lines if not l.startswith(">")).upper()


def extract_regions(genome: str, start: int, end: int, strand: str):
    """Cut the promoter, the start of the gene, and the whole gene.

    Database coordinates are 0-based with an exclusive end, so they
    index directly into the genome string with no adjustment.
    """
    n = len(genome)
    s0 = start              # coordinates are already 0-based
    e0 = end                # exclusive end

    if strand == "+":
        # Gene reads left to right. Upstream is to the LEFT of the start.
        up_from = max(0, s0 - UPSTREAM_BP)
        promoter = genome[up_from:s0]
        cds = genome[s0:e0]
    else:
        # Gene reads right to left. Upstream is to the RIGHT of the end,
        # and everything must be flipped to read in the gene's direction.
        up_to = min(n, e0 + UPSTREAM_BP)
        promoter = reverse_complement(genome[e0:up_to])
        cds = reverse_complement(genome[s0:e0])

    return promoter, cds[:CDS_HEAD_BP], cds


def main() -> None:
    print("=" * 66)
    print("BUILD TRAINING DATA — promoter sequence -> expression")
    print("=" * 66)

    print("\n[1] Loading genome")
    genome = load_genome()
    print(f"    {len(genome):,} bp")

    print("\n[2] Loading genes with expression values")
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT locus_tag, name, start_pos, end_pos, strand,
                   dna_sequence, reference_expression_tpm
            FROM genes
            WHERE reference_expression_tpm IS NOT NULL
              AND dna_sequence IS NOT NULL
            ORDER BY start_pos
        """)).fetchall()
    print(f"    {len(rows):,} genes")

    print("\n[3] Extracting promoters and validating coordinates")

    records = []
    mismatches = []
    short_promoters = 0

    for locus_tag, name, start, end, strand, stored_cds, tpm in rows:
        promoter, cds_head, cds = extract_regions(genome, start, end, strand)

        # Self-check: does the sequence we cut match what's in the DB?
        if cds != stored_cds.upper():
            mismatches.append(locus_tag)
            continue

        if len(promoter) < UPSTREAM_BP:
            short_promoters += 1

        records.append({
            "locus_tag": locus_tag,
            "gene_name": name or "",
            "strand": strand,
            "promoter": promoter,
            "cds_start": cds_head,
            "promoter_gc": round(
                (promoter.count("G") + promoter.count("C")) / max(len(promoter), 1), 4
            ),
            "reference_tpm": tpm,
            "log2_tpm": round(math.log2(tpm), 4) if tpm > 0 else None,
            "cds_length": len(cds),
        })

    ok = len(records)
    total = len(rows)
    print(f"    validated : {ok:,} / {total:,}  ({ok/total:.1%})")
    print(f"    mismatched: {len(mismatches):,}")
    if mismatches[:5]:
        print(f"    examples  : {mismatches[:5]}")
    if short_promoters:
        print(f"    short promoters (near genome edge): {short_promoters}")

    if ok / total < 0.9:
        print("\n    WARNING: too many mismatches. The coordinate or strand")
        print("    handling is probably wrong — do not train on this.")

    print("\n[4] Writing CSV")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    print(f"    {OUTPUT_PATH}  ({OUTPUT_PATH.stat().st_size/1e6:.1f} MB)")

    print("\n[5] Sanity check — genes we can reason about")
    by_tag = {r["locus_tag"]: r for r in records}
    for tag, why in [
        ("b0344", "lacZ — should be LOW, reference media is glucose"),
        ("b0002", "thrA — should be HIGH, amino acid synthesis"),
        ("b3702", "dnaA — should be MODERATE"),
    ]:
        r = by_tag.get(tag)
        if r:
            print(f"\n    {tag} {r['gene_name']:6} strand={r['strand']}  "
                  f"{r['reference_tpm']:>9,.1f} TPM")
            print(f"      {why}")
            print(f"      promoter ends: ...{r['promoter'][-40:]}")
            print(f"      gene starts  : {r['cds_start'][:20]}...")

    print("\n[6] Dataset summary")
    tpms = [r["reference_tpm"] for r in records]
    tpms.sort()
    print(f"    rows          : {len(records):,}")
    print(f"    promoter size : {UPSTREAM_BP} bp")
    print(f"    TPM min       : {tpms[0]:,.2f}")
    print(f"    TPM median    : {tpms[len(tpms)//2]:,.1f}")
    print(f"    TPM max       : {tpms[-1]:,.0f}")
    plus = sum(1 for r in records if r["strand"] == "+")
    print(f"    strand split  : {plus:,} (+) / {len(records)-plus:,} (-)")

    print("\n" + "=" * 66)
    print("Next: train a model to predict log2_tpm from the promoter column.")
    print("=" * 66)


if __name__ == "__main__":
    main()