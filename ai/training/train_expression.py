"""Train the expression predictor: promoter embeddings -> expression level.

Owned by: Keshav

Run on the HOST:
    python ai/training/train_expression.py

WHAT THIS DOES
--------------
Takes the 4,330 encoded promoters and learns to predict how active each
gene is.

THE HONEST TEST
---------------
The model trains on 80% of the genes and is then asked about the other
20% — genes it has never seen, not once. That is the only number worth
reporting.

A model can memorise 4,330 examples and score perfectly on them while
having learned nothing, like a student who memorised last year's paper.
Held-out genes are the real exam.

WHY GRADIENT BOOSTING, NOT A NEURAL NETWORK
-------------------------------------------
4,330 examples is a small dataset. Neural networks need far more before
they beat gradient boosting, and they overfit badly below that. Gradient
boosting trains in seconds, resists overfitting, and tells you which
features mattered.

BASELINES
---------
A model only earns its place by beating the dumb options:

    "always guess the average"  -- what you get with no model at all
    "guess from GC content"     -- one number, no deep learning needed

If the model cannot beat those, the embeddings are not helping.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

DATA_PATH = Path("data/training/encoded.npz")
MODEL_PATH = Path("data/models/expression_model.joblib")

SEED = 42
TEST_FRACTION = 0.2


def pearson(a, b) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def evaluate(name, y_true, y_pred, results):
    r = pearson(y_true, y_pred)
    results.append({
        "name": name,
        "r": r,
        "r2": r2_score(y_true, y_pred),
        "mae": mean_absolute_error(y_true, y_pred),
    })
    print(f"    {name:32} r={r:6.3f}   R2={r2_score(y_true, y_pred):7.3f}   "
          f"MAE={mean_absolute_error(y_true, y_pred):.3f}")
    return r


def main() -> None:
    print("=" * 70)
    print("TRAIN EXPRESSION PREDICTOR")
    print("=" * 70)

    # ------------------------------------------------------------------
    print("\n[1] Loading encoded promoters")
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"No encoded data at {DATA_PATH}. Run:\n"
            "  python ai/training/encode_promoters.py"
        )

    d = np.load(DATA_PATH, allow_pickle=True)
    X, y, tags = d["X"], d["y"], d["locus_tags"]
    print(f"    {X.shape[0]:,} genes, {X.shape[1]} features each")
    print(f"    target: log2 expression, range {y.min():.2f} to {y.max():.2f}")

    # ------------------------------------------------------------------
    print("\n[2] Splitting into train and test")
    X_tr, X_te, y_tr, y_te, tag_tr, tag_te = train_test_split(
        X, y, tags, test_size=TEST_FRACTION, random_state=SEED
    )
    print(f"    train: {len(X_tr):,} genes  (model learns from these)")
    print(f"    test : {len(X_te):,} genes  (model never sees these)")

    results = []

    # ------------------------------------------------------------------
    print("\n[3] Baselines — what we have to beat")
    print("    A model is only worth having if it beats the dumb options.\n")

    dummy = DummyRegressor(strategy="mean").fit(X_tr, y_tr)
    pred = dummy.predict(X_te)
    print(f"    {'always guess the average':32} r={'n/a':>6}   "
          f"R2={r2_score(y_te, pred):7.3f}   "
          f"MAE={mean_absolute_error(y_te, pred):.3f}")
    results.append({
        "name": "always guess the average", "r": 0.0,
        "r2": r2_score(y_te, pred), "mae": mean_absolute_error(y_te, pred),
    })

    ridge = Ridge(alpha=10.0).fit(X_tr, y_tr)
    evaluate("ridge regression (linear)", y_te, ridge.predict(X_te), results)

    # ------------------------------------------------------------------
    print("\n[4] Gradient boosting")
    t0 = time.perf_counter()
    model = HistGradientBoostingRegressor(
        max_iter=500,
        learning_rate=0.05,
        max_depth=6,
        min_samples_leaf=20,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=SEED,
    ).fit(X_tr, y_tr)
    print(f"    trained in {time.perf_counter() - t0:.1f}s "
          f"({model.n_iter_} boosting rounds)\n")

    r_train = pearson(y_tr, model.predict(X_tr))
    r_test = evaluate("gradient boosting (HELD OUT)", y_te,
                      model.predict(X_te), results)
    print(f"    {'(same model on training data)':32} r={r_train:6.3f}   "
          f"<- expect this to be higher")

    # ------------------------------------------------------------------
    print("\n[5] What the numbers mean")
    gap = r_train - r_test
    print(f"    held-out correlation : {r_test:.3f}")
    print(f"    training correlation : {r_train:.3f}")
    print(f"    gap                  : {gap:.3f}")

    if gap > 0.35:
        print("\n    Large gap — the model has partly memorised the training")
        print("    genes rather than learning general rules. Still usable,")
        print("    but more regularisation would help.")
    else:
        print("\n    Gap is reasonable — the model generalises rather than")
        print("    just memorising.")

    print()
    if r_test < 0.15:
        print("    VERDICT: no real signal. Promoter sequence alone is not")
        print("    predicting expression here. Something upstream is wrong,")
        print("    or this problem needs more than 300bp of context.")
    elif r_test < 0.35:
        print("    VERDICT: weak but real signal. Better than guessing, not")
        print("    yet useful on its own. Worth reporting honestly.")
    elif r_test < 0.55:
        print("    VERDICT: genuinely useful. This is in the range published")
        print("    methods reach for bacterial promoter strength prediction.")
    else:
        print("    VERDICT: strong result. Worth double-checking for leakage")
        print("    between train and test before celebrating.")

    # ------------------------------------------------------------------
    print("\n[6] Where the errors are")
    pred_te = model.predict(X_te)
    err = np.abs(pred_te - y_te)

    order = np.argsort(y_te)
    thirds = np.array_split(order, 3)
    labels = ["low expression", "medium expression", "high expression"]
    for lab, idx in zip(labels, thirds):
        print(f"    {lab:20} true {y_te[idx].mean():6.2f}   "
              f"predicted {pred_te[idx].mean():6.2f}   "
              f"avg error {err[idx].mean():.2f}")

    print("\n    Worst predictions:")
    for i in np.argsort(err)[-5:][::-1]:
        print(f"      {tag_te[i]:8} true={y_te[i]:6.2f}  "
              f"predicted={pred_te[i]:6.2f}  off by {err[i]:.2f}")

    # ------------------------------------------------------------------
    print("\n[7] Saving the model")
    import joblib

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "feature_dim": X.shape[1],
        "target": "log2_tpm",
        "test_r": r_test,
        "test_mae": mean_absolute_error(y_te, pred_te),
        "n_train": len(X_tr),
        "seed": SEED,
    }, MODEL_PATH)
    print(f"    {MODEL_PATH}  ({MODEL_PATH.stat().st_size/1e6:.1f} MB)")

    print("\n" + "=" * 70)
    print(f"HEADLINE: held-out correlation r = {r_test:.3f} on "
          f"{len(X_te):,} unseen genes")
    print("=" * 70)


if __name__ == "__main__":
    main()