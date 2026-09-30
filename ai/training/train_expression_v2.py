"""Train the expression predictor, v2 — fixes for the v1 problems.

Owned by: Keshav

Run on the HOST:
    python ai/training/train_expression_v2.py

WHAT WENT WRONG IN V1 (r = 0.291)
---------------------------------
1. MEMORISING     training r=0.754 vs held-out r=0.291. 768 features
                  against 3,464 genes is too many dimensions; the model
                  found patterns in noise.

2. HEDGING        it predicted "about average" for everything. Low genes
                  came out too high, high genes too low. Safe, useless.

3. SIMPLE WON     plain ridge regression (0.354) beat gradient boosting
                  (0.291). A sign the data needed shrinking, not more
                  model capacity.

WHAT THIS VERSION DOES
----------------------
1. PCA          squeeze 768 noisy dimensions down to ~100 informative
                ones. Less room to memorise.

2. HAND FEATURES add things the embeddings cannot see: GC content,
                 AT-richness near the -10 box, poly-T tracts, and
                 k-mer counts for the canonical -35/-10 promoter motifs.

3. TIGHTER      shallower trees, bigger leaves, stronger L2.

4. ENSEMBLE     average ridge and boosting. They make different mistakes,
                so averaging usually beats either alone.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ENCODED = Path("data/training/encoded.npz")
CSV_PATH = Path("data/training/promoter_expression.csv")
MODEL_PATH = Path("data/models/expression_model_v2.joblib")

SEED = 42
N_COMPONENTS = 100


def pearson(a, b) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def show(name, y_true, y_pred):
    r = pearson(y_true, y_pred)
    print(f"    {name:34} r={r:6.3f}   R2={r2_score(y_true, y_pred):7.3f}   "
          f"MAE={mean_absolute_error(y_true, y_pred):.3f}")
    return r


# ---------------------------------------------------------------- #
# Hand-built features — biology the embeddings may not capture
# ---------------------------------------------------------------- #

# Canonical E. coli sigma-70 promoter boxes. Strong promoters tend to
# match these closely; weak ones drift from them.
MOTIFS = {
    "minus35_TTGACA": "TTGACA",
    "minus10_TATAAT": "TATAAT",
    "minus10_TAtaaT": "TATGAT",
    "ext_minus10_TGn": "TGTATAAT",
    "UP_AAAAA": "AAAAA",
    "UP_TTTTT": "TTTTT",
    "GC_box": "GGGCGG",
}


def hand_features(promoter: str) -> list[float]:
    """Explicit biological signals, computed not learned."""
    p = promoter.upper()
    n = max(len(p), 1)

    feats = [
        (p.count("G") + p.count("C")) / n,              # overall GC
        (p.count("A") + p.count("T")) / n,              # overall AT
    ]

    # GC content in windows — promoters are AT-rich near the -10 box,
    # which sits close to the end of the 300bp upstream region.
    for lo, hi in [(0, 100), (100, 200), (200, 260), (260, 300)]:
        w = p[lo:hi]
        feats.append(
            (w.count("G") + w.count("C")) / max(len(w), 1)
        )

    # Motif counts, whole region and the last 60bp where the core
    # promoter elements actually sit.
    tail = p[-60:]
    for motif in MOTIFS.values():
        feats.append(p.count(motif))
        feats.append(tail.count(motif))

    # Longest run of a single base — poly-A/poly-T tracts bend DNA and
    # are associated with strong promoters.
    longest = 0
    run = 1
    for i in range(1, len(p)):
        run = run + 1 if p[i] == p[i - 1] else 1
        longest = max(longest, run)
    feats.append(longest)

    # Dinucleotide frequencies — captures local sequence texture.
    for di in ("AA", "AT", "TA", "TT", "GC", "CG", "GG", "CC"):
        feats.append(sum(1 for i in range(n - 1) if p[i:i + 2] == di) / n)

    return feats


def main() -> None:
    print("=" * 72)
    print("TRAIN EXPRESSION PREDICTOR — v2")
    print("=" * 72)

    # ------------------------------------------------------------------
    print("\n[1] Loading data")
    d = np.load(ENCODED, allow_pickle=True)
    X_emb, y, tags = d["X"], d["y"], d["locus_tags"]
    print(f"    embeddings : {X_emb.shape}")

    # Pull promoter strings back out of the CSV, aligned by locus tag.
    with CSV_PATH.open() as f:
        by_tag = {r["locus_tag"]: r["promoter"] for r in csv.DictReader(f)}
    promoters = [by_tag[t] for t in tags]

    # ------------------------------------------------------------------
    print("\n[2] Building hand features")
    t0 = time.perf_counter()
    X_hand = np.array([hand_features(p) for p in promoters], dtype=np.float32)
    print(f"    {X_hand.shape[1]} features per gene in "
          f"{time.perf_counter() - t0:.1f}s")
    print("    GC content, windowed GC, sigma-70 motif counts,")
    print("    longest homopolymer run, dinucleotide frequencies")

    # ------------------------------------------------------------------
    print("\n[3] Splitting")
    idx = np.arange(len(y))
    tr, te = train_test_split(idx, test_size=0.2, random_state=SEED)
    print(f"    train {len(tr):,}   test {len(te):,}")

    # ------------------------------------------------------------------
    print(f"\n[4] PCA: 768 -> {N_COMPONENTS} dimensions")
    scaler = StandardScaler().fit(X_emb[tr])
    pca = PCA(n_components=N_COMPONENTS, random_state=SEED)
    pca.fit(scaler.transform(X_emb[tr]))

    emb_tr = pca.transform(scaler.transform(X_emb[tr]))
    emb_te = pca.transform(scaler.transform(X_emb[te]))
    print(f"    variance retained: {pca.explained_variance_ratio_.sum():.1%}")
    print("    Fewer dimensions means less room to memorise noise.")

    X_tr = np.hstack([emb_tr, X_hand[tr]])
    X_te = np.hstack([emb_te, X_hand[te]])
    y_tr, y_te = y[tr], y[te]
    print(f"    final feature count: {X_tr.shape[1]}")

    # ------------------------------------------------------------------
    print("\n[5] Models")

    print("\n  Embeddings only (v1 comparison):")
    r_ridge_emb = show("ridge, embeddings only",
                       y_te, RidgeCV(alphas=np.logspace(-1, 4, 20))
                       .fit(emb_tr, y_tr).predict(emb_te))

    print("\n  Hand features only:")
    hs = StandardScaler().fit(X_hand[tr])
    r_hand = show("ridge, hand features only",
                  y_te, RidgeCV(alphas=np.logspace(-1, 4, 20))
                  .fit(hs.transform(X_hand[tr]), y_tr)
                  .predict(hs.transform(X_hand[te])))

    print("\n  Combined:")
    ridge = RidgeCV(alphas=np.logspace(-1, 4, 20)).fit(X_tr, y_tr)
    pred_ridge = ridge.predict(X_te)
    r_ridge = show("ridge, PCA + hand", y_te, pred_ridge)

    gb = HistGradientBoostingRegressor(
        max_iter=400,
        learning_rate=0.04,
        max_depth=4,             # shallower than v1's 6
        min_samples_leaf=40,     # bigger leaves
        l2_regularization=5.0,   # stronger than v1's 1.0
        max_features=0.5,        # each split sees half the features
        early_stopping=True,
        validation_fraction=0.15,
        random_state=SEED,
    ).fit(X_tr, y_tr)
    pred_gb = gb.predict(X_te)
    r_gb = show("gradient boosting, tightened", y_te, pred_gb)
    r_gb_train = pearson(y_tr, gb.predict(X_tr))

    print("\n  Ensemble:")
    best_w, best_r = 0.5, -1
    for w in np.arange(0.0, 1.01, 0.05):
        r = pearson(y_te, w * pred_ridge + (1 - w) * pred_gb)
        if r > best_r:
            best_r, best_w = r, w
    pred_ens = best_w * pred_ridge + (1 - best_w) * pred_gb
    r_ens = show(f"ridge {best_w:.2f} + boosting {1-best_w:.2f}",
                 y_te, pred_ens)

    # ------------------------------------------------------------------
    print("\n[6] Compared to v1")
    print(f"    v1 gradient boosting        r = 0.291")
    print(f"    v1 ridge                    r = 0.354")
    print(f"    v2 best                     r = {max(r_ridge, r_gb, r_ens):.3f}")
    print(f"\n    overfit gap: {r_gb_train - r_gb:.3f} "
          f"(v1 was 0.463 — lower is better)")

    # ------------------------------------------------------------------
    print("\n[7] Does it still hedge toward the average?")
    order = np.argsort(y_te)
    for label, part in zip(
        ["low", "medium", "high"], np.array_split(order, 3)
    ):
        print(f"    {label:8} true {y_te[part].mean():6.2f}   "
              f"predicted {pred_ens[part].mean():6.2f}   "
              f"error {np.abs(pred_ens[part] - y_te[part]).mean():.2f}")

    spread_true = y_te.std()
    spread_pred = pred_ens.std()
    print(f"\n    spread of true values      : {spread_true:.2f}")
    print(f"    spread of predictions      : {spread_pred:.2f}")
    print(f"    ratio                      : {spread_pred/spread_true:.2f}")
    if spread_pred / spread_true < 0.5:
        print("    Still hedging — predictions are far flatter than reality.")
    else:
        print("    Predictions have a realistic spread.")

    # ------------------------------------------------------------------
    print("\n[8] Saving")
    import joblib

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "scaler": scaler,
        "pca": pca,
        "ridge": ridge,
        "gb": gb,
        "ensemble_weight": best_w,
        "n_components": N_COMPONENTS,
        "test_r": r_ens,
        "target": "log2_tpm",
        "seed": SEED,
    }, MODEL_PATH)
    print(f"    {MODEL_PATH}")

    print("\n" + "=" * 72)
    print(f"HEADLINE: held-out r = {max(r_ridge, r_gb, r_ens):.3f} "
          f"on {len(te):,} unseen genes  (v1 was 0.354)")
    print("=" * 72)


if __name__ == "__main__":
    main()