"""Inspect PRECISE-1K annotation data against our genes table.

Owned by: Keshav

WHAT THIS IS
------------
PRECISE-1K is a published RNA-seq compendium for E. coli K-12 MG1655,
built by the same lab that produced iML1515. Two small annotation files
from it give us things we currently lack:

  gene_info.csv  (1.0 MB)  — per-gene reference expression level under
                             control conditions (wild-type, glucose M9),
                             plus iML1515 membership and essentiality

  TRN.csv        (0.4 MB)  — 10,790 regulator to gene interactions,
                             versus the 38 we have today

WHAT THIS SCRIPT DOES
---------------------
Downloads both files, then answers one question before we build anything
on top of them: do PRECISE's gene identifiers actually match ours?

It changes nothing in the database. Read-only, safe to run repeatedly.

    python ai/training/inspect_precise.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd  # noqa: E402
import requests  # noqa: E402

BASE = "https://raw.githubusercontent.com/SBRG/precise1k/main/data"
FILES = {
    "gene_info.csv": f"{BASE}/annotation/gene_info.csv",
    "TRN.csv": f"{BASE}/annotation/TRN.csv",
}

DATA_DIR = Path("data/precise")

DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://biosandbox:biosandbox@localhost:5432/biosandbox",
)

# The column holding log2(TPM) under the reference condition:
# wild-type E. coli growing on glucose M9 minimal media. This matches
# the reference our contract defines (37C, pH 7, aerobic, glucose,
# ammonium) — M9 supplies ammonium as the nitrogen source.
REF_COL = "p1k_ctrl_log_tpm"


def download() -> None:
    """Fetch the two annotation files if we don't already have them."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for name, url in FILES.items():
        target = DATA_DIR / name
        if target.exists():
            print(f"  {name}: already present ({target.stat().st_size/1e6:.2f} MB)")
            continue

        print(f"  {name}: downloading...", end=" ", flush=True)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        target.write_bytes(resp.content)
        print(f"{len(resp.content)/1e6:.2f} MB")


def load_our_genes() -> pd.DataFrame:
    """Read locus tags and names out of our own genes table."""
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT locus_tag, name FROM genes")
        ).fetchall()

    return pd.DataFrame(rows, columns=["locus_tag", "name"])


def main() -> None:
    print("=" * 66)
    print("PRECISE-1K inspection")
    print("=" * 66)

    print("\n[1] Downloading annotation files")
    download()

    print("\n[2] Loading data")
    gene_info = pd.read_csv(DATA_DIR / "gene_info.csv")
    trn = pd.read_csv(DATA_DIR / "TRN.csv")
    ours = load_our_genes()

    print(f"  PRECISE gene_info : {len(gene_info):,} genes")
    print(f"  PRECISE TRN       : {len(trn):,} interactions")
    print(f"  our genes table   : {len(ours):,} genes")

    # ---------------------------------------------------------------- #
    # The question that matters: do the identifiers line up?
    # ---------------------------------------------------------------- #
    print("\n[3] Do the gene IDs match?")

    precise_tags = set(gene_info["locus_tag"].str.lower())
    our_tags = set(ours["locus_tag"].str.lower())

    both = precise_tags & our_tags
    only_ours = our_tags - precise_tags
    only_precise = precise_tags - our_tags

    print(f"  in both            : {len(both):,}")
    print(f"  only in our DB     : {len(only_ours):,}  (no expression data)")
    print(f"  only in PRECISE    : {len(only_precise):,}  (not in our DB)")
    print(f"  coverage of our DB : {len(both)/len(our_tags):.1%}")

    if only_ours:
        print(f"  examples missing   : {sorted(only_ours)[:5]}")

    # ---------------------------------------------------------------- #
    # Reference expression — the number Track A needs
    # ---------------------------------------------------------------- #
    print(f"\n[4] Reference expression ({REF_COL})")

    ref = gene_info[["locus_tag", "gene_name", REF_COL, "iML1515"]].copy()
    ref["tpm"] = 2 ** ref[REF_COL]          # undo the log2

    print(f"  genes with a value : {ref[REF_COL].notna().sum():,} / {len(ref):,}")
    print(f"  TPM range          : {ref.tpm.min():.2f} to {ref.tpm.max():,.0f}")
    print(f"  median TPM         : {ref.tpm.median():.1f}")

    print("\n  sanity check — a few genes we can reason about:")
    checks = {
        "b0344": "lacZ, lactose digestion. Reference media is GLUCOSE, "
                 "so this should be nearly off",
        "b0002": "thrA, amino acid synthesis. Minimal media, so should be high",
        "b3702": "dnaA, replication initiator. Steady moderate level",
    }
    for tag, why in checks.items():
        row = ref[ref.locus_tag.str.lower() == tag]
        if len(row):
            row = row.iloc[0]
            print(f"    {tag} {str(row.gene_name):6} {row.tpm:9,.1f} TPM")
            print(f"           {why}")

    # ---------------------------------------------------------------- #
    # Regulatory network
    # ---------------------------------------------------------------- #
    print("\n[5] Transcriptional regulatory network")
    print(f"  interactions       : {len(trn):,}")
    print(f"  regulators         : {trn.regulator.nunique():,}")
    print(f"  genes regulated    : {trn.gene_id.nunique():,}")

    matched = trn[trn.gene_id.str.lower().isin(our_tags)]
    print(f"  usable with our DB : {len(matched):,} "
          f"({len(matched)/len(trn):.0%} of interactions)")

    print("\n  effect breakdown:")
    for effect, n in trn.effect.value_counts().items():
        label = {"+": "activator", "-": "repressor", "?": "unknown"}.get(
            str(effect), str(effect)
        )
        print(f"    {str(effect):3} {label:12} {n:6,}")

    # ---------------------------------------------------------------- #
    # Overlap with the metabolic model
    # ---------------------------------------------------------------- #
    print("\n[6] Overlap with iML1515")
    in_iml = ref[ref.iML1515 == True]  # noqa: E712
    print(f"  genes in iML1515   : {len(in_iml):,}")
    print(f"  ...with expression : {in_iml[REF_COL].notna().sum():,}")
    print("  (these are the genes that actually affect the simulation)")

    print("\n" + "=" * 66)
    print("Files are in", DATA_DIR.resolve())
    print("=" * 66)


if __name__ == "__main__":
    main()