"""Each gene's track record from the essential-gene check.

backend/validation/essentiality.py knocks out every gene in iML1515 and
compares the result with the lab's essential-gene list (PRECISE-1K). It
writes one row per gene to validation/results/essentiality_genes.csv,
which is committed to the repo. This module reads that file so the app can
show, next to a knockout, what the lab found and whether GENESIS agreed.

Both the lab data and that screen are for RICH medium (LB broth). A gene
can be harmless to lose in LB, where the cell imports what it needs, yet
lethal on a minimal medium. The UI must say which medium a record is for.

If the file is missing (the check has not been run), every lookup returns
None and the app simply shows no record.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

# app/services/ -> app/ -> backend root (/app in Docker)
RECORD_PATH = Path(__file__).resolve().parents[2] / "validation" / "results" / "essentiality_genes.csv"


@lru_cache(maxsize=1)
def _load() -> dict[str, dict]:
    if not RECORD_PATH.exists():
        return {}
    records = {}
    with RECORD_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records[row["locus_tag"]] = {
                "lab_essential": row["essential"] == "True",
                "model_essential": row["predicted_essential"] == "True",
                # TP / TN = GENESIS agreed with the lab; FP / FN = it did not
                "outcome": row["outcome"],
                "agrees": row["outcome"] in ("TP", "TN"),
            }
    return records


def record_for(locus_tag: str) -> dict | None:
    """The lab call and GENESIS's call for one gene, or None if not screened."""
    return _load().get(locus_tag)