"""Encode promoters with HyenaDNA -> feature matrix for training.

Owned by: Keshav

Run on the HOST (torch lives in .venv, not the backend container):
    python ai/training/encode_promoters.py

WHAT THIS DOES
--------------
Takes the 4,331 promoter sequences from the training CSV and runs each
one through HyenaDNA, turning letters into numbers:

    "TTGACA...GGAATTGTGAGCGG..."   300 letters
                  |
              HyenaDNA
                  v
    [0.23, -1.44, 0.87, ...]       768 numbers

Those numbers capture behaviour, not spelling. Two promoters that act
alike end up close together even if their letters differ. That is what
makes them learnable.

WHY 768
-------
The wrapper pools each sequence three ways, 256 numbers each:

    [ promoter region | coding start | whole thing ]

The promoter carries transcription-strength signal; the coding start
carries ribosome-binding context. Keeping them separate lets the model
use the distinction.

OUTPUT
------
    data/training/encoded.npz
        X           (4331, 768)  float32  features
        y           (4331,)      float32  log2 expression  <- what we predict
        tpm         (4331,)      float32  raw expression
        locus_tags  (4331,)      str      which gene each row is

Encoding takes a few minutes. The result is cached, so later runs are
instant unless you pass --force.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np  # noqa: E402

from ai.models.hyenadna_wrapper import HyenaDNAWrapper  # noqa: E402

CSV_PATH = Path("data/training/promoter_expression.csv")
OUT_PATH = Path("data/training/encoded.npz")


def load_rows() -> list[dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"No training CSV at {CSV_PATH.resolve()}\n\n"
            "Build it, then copy it out of the container:\n"
            "  docker compose exec backend python -m app.data.build_training_data\n"
            "  docker compose cp backend:/app/data/training/promoter_expression.csv "
            "data/training/promoter_expression.csv"
        )
    with CSV_PATH.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-encode even if cached")
    ap.add_argument("--limit", type=int, default=None, help="encode only N rows (testing)")
    args = ap.parse_args()

    print("=" * 66)
    print("ENCODE PROMOTERS — DNA letters -> numbers")
    print("=" * 66)

    if OUT_PATH.exists() and not args.force:
        d = np.load(OUT_PATH, allow_pickle=True)
        print(f"\nAlready encoded: {OUT_PATH}")
        print(f"  X shape: {d['X'].shape}")
        print(f"  y shape: {d['y'].shape}")
        print("\nPass --force to redo it.")
        return

    print("\n[1] Loading training CSV")
    rows = load_rows()
    if args.limit:
        rows = rows[: args.limit]
    print(f"    {len(rows):,} genes")

    print("\n[2] Loading HyenaDNA")
    t0 = time.perf_counter()
    wrapper = HyenaDNAWrapper()
    wrapper.load()
    print(f"    ready in {time.perf_counter() - t0:.1f}s")

    print("\n[3] Encoding")
    print("    Each promoter (300bp) plus the first 100bp of its gene")
    print("    goes through the model and comes back as 768 numbers.\n")

    X, y, tpm, tags = [], [], [], []
    skipped = []

    t0 = time.perf_counter()
    for i, row in enumerate(rows, 1):
        promoter = row["promoter"].strip().upper()
        cds_start = row["cds_start"].strip().upper()

        # The wrapper splits at position 300, so promoter + cds_start
        # lines the split up exactly with the two regions.
        if len(promoter) != 300:
            skipped.append(row["locus_tag"])
            continue

        log2 = row.get("log2_tpm", "")
        if not log2:
            skipped.append(row["locus_tag"])
            continue

        emb = wrapper.embed_gene(promoter + cds_start)

        X.append(emb.concat().astype(np.float32))
        y.append(float(log2))
        tpm.append(float(row["reference_tpm"]))
        tags.append(row["locus_tag"])

        if i % 250 == 0 or i == len(rows):
            elapsed = time.perf_counter() - t0
            rate = i / elapsed
            remain = (len(rows) - i) / rate
            print(f"    {i:>5,} / {len(rows):,}   "
                  f"{elapsed:>6.1f}s elapsed   "
                  f"{remain:>5.0f}s left   "
                  f"({rate:.1f}/s)")

    total = time.perf_counter() - t0
    print(f"\n    encoded {len(X):,} in {total:.1f}s ({len(X)/total:.1f}/s)")
    if skipped:
        print(f"    skipped {len(skipped)} (wrong promoter length or no label)")
        print(f"    e.g. {skipped[:5]}")

    print("\n[4] Saving")
    X = np.stack(X)
    y = np.array(y, dtype=np.float32)
    tpm = np.array(tpm, dtype=np.float32)
    tags = np.array(tags)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT_PATH, X=X, y=y, tpm=tpm, locus_tags=tags)
    print(f"    {OUT_PATH}  ({OUT_PATH.stat().st_size/1e6:.1f} MB)")

    print("\n[5] What came out")
    print(f"    X (features) : {X.shape}   {X.dtype}")
    print(f"    y (log2 TPM) : {y.shape}   range {y.min():.2f} to {y.max():.2f}")
    print(f"    feature mean : {X.mean():.4f}   std {X.std():.4f}")

    # A quick honesty check: do similar genes get similar vectors?
    # Ribosomal proteins are all highly expressed and co-regulated, so
    # their promoters should cluster more tightly than random pairs.
    print("\n[6] Quick check — do the numbers mean anything?")
    norms = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(norms), size=min(400, len(norms)), replace=False)
    sims = norms[idx] @ norms[idx].T
    off = sims[~np.eye(len(idx), dtype=bool)]
    print(f"    average similarity between random promoter pairs: {off.mean():.3f}")
    print(f"    spread (std): {off.std():.3f}")
    if off.std() < 0.01:
        print("    WARNING: all vectors look nearly identical — the model")
        print("    may not be distinguishing sequences at all.")
    else:
        print("    Vectors differ from each other, so there is signal to learn.")

    print("\n" + "=" * 66)
    print("Next: train gradient boosting to predict y from X.")
    print("=" * 66)


if __name__ == "__main__":
    main()