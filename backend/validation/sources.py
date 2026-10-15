"""Where the ground truth comes from.

Both checks use files from PRECISE-1K, the E. coli RNA-seq compendium from
the Palsson lab (the group that also built iML1515):

    gene_info.csv  — one row per gene; the `essential` column is used by
                     the essentiality check
    metadata.csv   — one row per experiment; `Growth Rate (1/hr)` and the
                     culture conditions are used by the growth-rate check

The URLs are pinned to one commit, not to `main`. If the lab edits these
files later, our results do not silently change. To move to newer data,
change PRECISE_COMMIT on purpose and re-run both checks.

Files are downloaded once and cached in validation/data/ (git-ignored).
"""

from __future__ import annotations

from pathlib import Path

import httpx

PRECISE_COMMIT = "4829b83ace51ee7980de6950077f1cf8f3746f88"
_BASE = f"https://raw.githubusercontent.com/SBRG/precise1k/{PRECISE_COMMIT}/data"

FILES = {
    "gene_info.csv": f"{_BASE}/annotation/gene_info.csv",
    "metadata.csv": f"{_BASE}/precise1k/metadata.csv",
}

# Shown in every report so a reader can check the source themselves
CITATION = (
    "PRECISE-1K — Lamoureux et al., \"A multi-scale expression and regulation "
    "knowledge base for Escherichia coli\", Nucleic Acids Research 51(19):10176 (2023), "
    f"doi:10.1093/nar/gkad750; data from github.com/SBRG/precise1k at commit {PRECISE_COMMIT[:7]}"
)

VALIDATION_DIR = Path(__file__).resolve().parent
DATA_DIR = VALIDATION_DIR / "data"
RESULTS_DIR = VALIDATION_DIR / "results"


def fetch(name: str) -> Path:
    """Return the local path of a PRECISE file, downloading it the first time."""
    if name not in FILES:
        raise KeyError(f"Unknown file {name!r}; expected one of {sorted(FILES)}")
    path = DATA_DIR / name
    if path.exists() and path.stat().st_size > 0:
        return path

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {name} from PRECISE-1K ({PRECISE_COMMIT[:7]})...", end=" ", flush=True)
    resp = httpx.get(FILES[name], follow_redirects=True, timeout=60)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    print(f"{len(resp.content) / 1e6:.1f} MB")
    return path


def results_dir() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR