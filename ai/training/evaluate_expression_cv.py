"""Honest evaluation of the expression predictor — operon-grouped cross-validation.

Owned by: Keshav

Run on the HOST (needs data/training/encoded.npz and the database):
    python ai/training/evaluate_expression_cv.py

WHY THIS EXISTS
---------------
`train_expression_v2.py` reports r = 0.378, but that number has three
weaknesses a reviewer will find:

1. ONE SPLIT        The data is cut 80/20 once. Nobody can tell how much
                    the score would move on a different draw.

2. TEST SET PEEKED  The ridge/boosting mixing weight is chosen by trying
                    every value and keeping whichever scores best ON THE
                    TEST SET. The headline is then the best of three
                    models, also judged on the test set. Both choices make
                    the number flattering.

3. OPERON LEAKAGE   E. coli genes are transcribed in groups (operons) that
                    share one promoter. Genes inside an operon overlap in
                    sequence with their neighbours. A random split can put
                    geneA in train and geneB in test, so the model is
                    partly tested on DNA it has already seen.

WHAT THIS SCRIPT DOES INSTEAD
-----------------------------
* 5-fold cross-validation, so every gene is predicted exactly once while
  being out of the training set. The score is a mean +/- spread, not one
  lucky number.
* Genes from the same operon always land in the SAME fold (GroupKFold),
  so no gene is tested against its own neighbour's DNA.
* The mixing weight is chosen inside the training part of each fold, on an
  inner validation slice. The test fold is never looked at until scoring.
* Baselines are scored the same way: predicting the mean, GC content only,
  hand features only, embeddings only. A model is only worth reporting if
  it beats these.
* The same run is repeated with plain random folds, so the size of the
  operon leak is measurable instead of assumed.

NOTHING IS SAVED. This script measures; it does not ship a model.
`train_expression_v2.py` still produces the model the app loads.

OUTPUT
------
    data/training/cv_results.json   every fold's score, for the paper
    printed table                   mean +/- standard deviation per model
"""

from __future__ import annotations

import csv
import os
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold, KFold, train_test_split
from sklearn.preprocessing import StandardScaler

ENCODED = Path("data/training/encoded.npz")
CSV_PATH = Path("data/training/promoter_expression.csv")
RESULTS = Path("data/training/cv_results.json")

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://biosandbox:biosandbox@localhost:5432/biosandbox",
)

SEED = 42
N_FOLDS = 5
N_COMPONENTS = 100
GAP_THRESHOLD = 50       # same rule as train_operon_aware.py

# Hand-built promoter features — identical to train_expression_v2.py, so
# the comparison is like for like.
MOTIFS = ["TTGACA", "TATAAT", "TATGAT", "TGTATAAT", "AAAAA", "TTTTT", "GGGCGG"]


def hand_features(promoter: str) -> list[float]:
    p = promoter.upper()
    n = max(len(p), 1)
    feats = [
        (p.count("G") + p.count("C")) / n,
        (p.count("A") + p.count("T")) / n,
    ]
    for lo, hi in [(0, 100), (100, 200), (200, 260), (260, 300)]:
        w = p[lo:hi]
        feats.append((w.count("G") + w.count("C")) / max(len(w), 1))
    tail = p[-60:]
    for m in MOTIFS:
        feats.append(p.count(m))
        feats.append(tail.count(m))
    longest, run = 0, 1
    for i in range(1, len(p)):
        run = run + 1 if p[i] == p[i - 1] else 1
        longest = max(longest, run)
    feats.append(longest)
    for di in ("AA", "AT", "TA", "TT", "GC", "CG", "GG", "CC"):
        feats.append(sum(1 for i in range(n - 1) if p[i:i + 2] == di) / n)
    return feats


def pearson(a, b) -> float:
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


# ------------------------------------------------------------------ #
# Operon groups
# ------------------------------------------------------------------ #

def load_positions() -> dict[str, tuple[int, int, str]]:
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT locus_tag, start_pos, end_pos, strand FROM genes "
            "WHERE start_pos IS NOT NULL ORDER BY start_pos"
        )).fetchall()
    return {r[0]: (r[1], r[2], r[3]) for r in rows}


def operon_groups(positions: dict[str, tuple[int, int, str]],
                  gap: int = GAP_THRESHOLD) -> dict[str, int]:
    """Give every gene a transcription-unit number.

    Two genes share a number when they point the same way and sit closer
    than `gap` base pairs apart — the signature of being read as one
    message. A gene whose upstream neighbour points away, or is far off,
    starts a new unit because it must carry its own promoter.

    Returns {locus_tag: group number}. Genes with no coordinates get a
    group of their own so they never pull others along.
    """
    genes = sorted(
        ((tag, s, e, st) for tag, (s, e, st) in positions.items()),
        key=lambda g: g[1],
    )

    # A gene is "chained" to its upstream neighbour when they are
    # co-transcribed. Walk the chromosome once and number the runs.
    group: dict[str, int] = {}
    current = 0

    for i, (tag, start, end, strand) in enumerate(genes):
        chained_to_previous = False
        if strand == "+" and i > 0:
            _, _, prev_end, prev_strand = genes[i - 1]
            chained_to_previous = prev_strand == "+" and (start - prev_end) < gap
        # A '-' strand gene is read right to left, so its upstream
        # neighbour sits at higher coordinates: it chains FORWARD in
        # coordinate order instead. Handled by the second pass below.
        if not chained_to_previous:
            current += 1
        group[tag] = current

    # Second pass for the minus strand: a run of '-' genes packed together
    # is one unit, so merge each '-' gene with the '-' gene after it.
    for i in range(len(genes) - 2, -1, -1):
        tag, start, end, strand = genes[i]
        if strand != "-":
            continue
        nxt_tag, nxt_start, _, nxt_strand = genes[i + 1]
        if nxt_strand == "-" and (nxt_start - end) < gap:
            # same unit: adopt the downstream gene's number
            old, new = group[tag], group[nxt_tag]
            if old != new:
                for t, g in group.items():
                    if g == old:
                        group[t] = new
    return group


# ------------------------------------------------------------------ #
# One fold
# ------------------------------------------------------------------ #

def fit_predict(X_tr, y_tr, X_te, use_pca: bool):
    """Train the v2 ensemble on a training fold and predict the test fold.

    The mixing weight is chosen on an inner slice of the TRAINING data.
    The test fold is untouched until the prediction is returned.
    """
    scaler = StandardScaler().fit(X_tr)
    Xtr = scaler.transform(X_tr)
    Xte = scaler.transform(X_te)

    if use_pca:
        n_comp = min(N_COMPONENTS, Xtr.shape[0] - 1, Xtr.shape[1])
        pca = PCA(n_components=n_comp, random_state=SEED).fit(Xtr)
        Xtr, Xte = pca.transform(Xtr), pca.transform(Xte)

    # Inner split: pick the ensemble weight without seeing the test fold.
    inner_tr, inner_va = train_test_split(
        np.arange(len(y_tr)), test_size=0.2, random_state=SEED
    )
    ridge_in = RidgeCV(alphas=np.logspace(-1, 4, 20)).fit(Xtr[inner_tr], y_tr[inner_tr])
    gb_in = _gb().fit(Xtr[inner_tr], y_tr[inner_tr])
    p_r = ridge_in.predict(Xtr[inner_va])
    p_g = gb_in.predict(Xtr[inner_va])

    best_w, best_r = 0.5, -np.inf
    for w in np.arange(0, 1.01, 0.05):
        r = pearson(y_tr[inner_va], w * p_r + (1 - w) * p_g)
        if r == r and r > best_r:          # r == r filters out NaN
            best_r, best_w = r, float(w)

    # Refit both models on the whole training fold with that weight.
    ridge = RidgeCV(alphas=np.logspace(-1, 4, 20)).fit(Xtr, y_tr)
    gb = _gb().fit(Xtr, y_tr)
    pred = best_w * ridge.predict(Xte) + (1 - best_w) * gb.predict(Xte)
    return pred, best_w


def _gb():
    return HistGradientBoostingRegressor(
        max_iter=400, learning_rate=0.04, max_depth=4,
        min_samples_leaf=40, l2_regularization=5.0, max_features=0.5,
        early_stopping=True, validation_fraction=0.15, random_state=SEED,
    )


def cross_validate(feature_sets: dict, y, groups, splitter, label: str) -> dict:
    """Score every model under one splitting rule."""
    print(f"\n{label}")
    print(f"  {'model':28} {'r (mean +/- sd)':>20}  {'MAE':>6}  per fold")

    results = {}
    folds = list(splitter.split(np.zeros((len(y), 1)), y, groups))

    for name, (X, use_pca) in feature_sets.items():
        rs, maes = [], []
        for tr, te in folds:
            if X is None:                      # "predict the mean" baseline
                pred = np.full(len(te), y[tr].mean())
                rs.append(float("nan"))        # a flat line has no correlation
            else:
                pred, _ = fit_predict(X[tr], y[tr], X[te], use_pca)
                rs.append(pearson(y[te], pred))
            maes.append(mean_absolute_error(y[te], pred))
        rs, maes = np.array(rs, dtype=float), np.array(maes, dtype=float)
        if np.all(np.isnan(rs)):
            # A constant prediction has no correlation to report — only MAE.
            print(f"  {name:28} {'n/a (constant)':>20}  {np.mean(maes):6.3f}")
            r_mean = r_sd = float("nan")
        else:
            each = " ".join(f"{v:.3f}" for v in rs)
            r_mean, r_sd = float(np.nanmean(rs)), float(np.nanstd(rs))
            print(f"  {name:28} {r_mean:8.3f} +/- {r_sd:.3f}  "
                  f"{np.mean(maes):6.3f}  {each}")
        results[name] = {
            "r_mean": r_mean,
            "r_sd": r_sd,
            "r_per_fold": [float(v) for v in rs],
            "mae_mean": float(np.mean(maes)),
        }
    return results


def main() -> None:
    print("=" * 74)
    print("EXPRESSION PREDICTOR — CROSS-VALIDATED EVALUATION")
    print("=" * 74)

    print("\n[1] Loading encoded promoters")
    d = np.load(ENCODED, allow_pickle=True)
    X_emb, y, tags = d["X"], d["y"].astype(float), d["locus_tags"]
    print(f"    {len(tags):,} genes, {X_emb.shape[1]} embedding dimensions")

    with CSV_PATH.open() as f:
        prom_by_tag = {r["locus_tag"]: r["promoter"] for r in csv.DictReader(f)}
    promoters = [prom_by_tag[t] for t in tags]

    print("\n[2] Building hand features")
    X_hand = np.array([hand_features(p) for p in promoters], dtype=np.float32)
    X_gc = X_hand[:, :1]                       # overall GC content alone
    X_both = np.hstack([X_emb, X_hand])
    print(f"    {X_hand.shape[1]} hand features per gene")

    print("\n[3] Grouping genes into transcription units")
    positions = load_positions()
    gmap = operon_groups(positions)
    missing = [t for t in tags if t not in gmap]
    next_id = max(gmap.values(), default=0)
    for t in missing:                          # unknown position = its own unit
        next_id += 1
        gmap[t] = next_id
    groups = np.array([gmap[t] for t in tags])
    sizes = np.bincount(np.unique(groups, return_inverse=True)[1])
    print(f"    {len(set(groups)):,} units over {len(tags):,} genes "
          f"(largest {sizes.max()} genes, {(sizes == 1).sum():,} single-gene units)")
    if missing:
        print(f"    {len(missing)} gene(s) had no coordinates and were left alone")

    feature_sets = {
        "predict the mean": (None, False),
        "GC content only": (X_gc, False),
        "hand features only": (X_hand, False),
        "HyenaDNA embeddings only": (X_emb, True),
        "embeddings + hand (v2)": (X_both, True),
    }

    print(f"\n[4] {N_FOLDS}-fold cross-validation")
    grouped = cross_validate(
        feature_sets, y, groups, GroupKFold(n_splits=N_FOLDS),
        "  A. Operon-grouped folds (the number to report)",
    )
    random_folds = cross_validate(
        feature_sets, y, None, KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED),
        "  B. Random folds (for comparison — leaks operon neighbours)",
    )

    headline = grouped["embeddings + hand (v2)"]
    leak = random_folds["embeddings + hand (v2)"]["r_mean"] - headline["r_mean"]

    print("\n" + "=" * 74)
    print(f"HEADLINE: r = {headline['r_mean']:.3f} +/- {headline['r_sd']:.3f} "
          f"over {N_FOLDS} operon-grouped folds")
    print(f"  Random folds give {random_folds['embeddings + hand (v2)']['r_mean']:.3f}, "
          f"so operon leakage is worth about {leak:+.3f}.")
    print(f"  Beats hand features alone by "
          f"{headline['r_mean'] - grouped['hand features only']['r_mean']:+.3f}.")
    print("  Quote the grouped number in the paper, and say the weight was")
    print("  chosen inside each training fold.")
    print("=" * 74)

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps({
        "n_genes": int(len(y)),
        "n_folds": N_FOLDS,
        "n_operon_units": int(len(set(groups))),
        "gap_threshold_bp": GAP_THRESHOLD,
        "seed": SEED,
        "target": "log2_tpm",
        "operon_grouped": grouped,
        "random_folds": random_folds,
    }, indent=2))
    print(f"\nWrote {RESULTS}")


if __name__ == "__main__":
    main()
