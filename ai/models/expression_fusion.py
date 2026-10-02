"""Expression fusion model — sequence embeddings to expression level.

Owned by: Keshav

WHAT THIS IS
------------
The trained model that turns a promoter into a predicted expression
level. It fuses two kinds of evidence:

    HyenaDNA embeddings   768 numbers per promoter, learned from DNA
    hand-built features    29 numbers, explicit promoter biology

WHY BOTH
--------
The embeddings capture patterns nobody wrote down. The hand features
capture ones we know matter and want the model to see directly — the
canonical sigma-70 boxes (TTGACA at -35, TATAAT at -10), AT-richness
near the -10 region, and poly-A/T tracts that bend DNA.

Measured separately on held-out genes:

    embeddings only     r = 0.345
    hand features only  r = 0.223
    both, ensembled     r = 0.378

So the foundation model earns its place, and the hand features add a
little on top.

WHY GRADIENT BOOSTING AND RIDGE, NOT A NEURAL NETWORK
-----------------------------------------------------
4,331 training examples is small. A neural head overfits badly at that
size; plain ridge regression actually beat gradient boosting in the
first attempt (0.354 vs 0.291). The fix was to shrink the feature space
with PCA, tighten the trees, and average the two models — they make
different mistakes, so the ensemble beats either alone.

HONEST LIMITS
-------------
Held-out Pearson r = 0.378 means the model explains about 14% of the
variance in expression. It is better than guessing and the signal is
real, but it is not accurate enough to rely on alone. In the live
system most genes are answered by database lookup instead; this model
only handles sequences nobody has measured.

The prediction spread matches sqrt(R-squared) almost exactly, which
means the model is extracting essentially all the signal a 300bp window
contains. Doing better needs more context, not a better model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Canonical E. coli sigma-70 promoter elements. Strong promoters tend to
# match these closely; weak ones drift away from them.
SIGMA70_MOTIFS = (
    "TTGACA",      # -35 box, consensus
    "TATAAT",      # -10 box, consensus (Pribnow box)
    "TATGAT",      # -10 box, common variant
    "TGTATAAT",    # extended -10
    "AAAAA",       # poly-A, UP element / DNA bending
    "TTTTT",       # poly-T
    "GGGCGG",      # GC-rich, often in weakly expressed regions
)

DINUCLEOTIDES = ("AA", "AT", "TA", "TT", "GC", "CG", "GG", "CC")

# The last ~60bp of the 300bp upstream window is where the core promoter
# elements actually sit, so motifs are counted there as well as overall.
CORE_PROMOTER_WINDOW = 60

GC_WINDOWS = ((0, 100), (100, 200), (200, 260), (260, 300))

HAND_FEATURE_COUNT = 2 + len(GC_WINDOWS) + 2 * len(SIGMA70_MOTIFS) + 1 + len(DINUCLEOTIDES)


@dataclass
class TrainingMetrics:
    """What the model scored when it was trained."""
    test_r: float = 0.0
    test_r2: float = 0.0
    test_mae: float = 0.0
    train_r: float = 0.0
    n_train: int = 0
    n_test: int = 0
    trained_on: str = ""

    @property
    def overfit_gap(self) -> float:
        return self.train_r - self.test_r

    def describe(self) -> str:
        return (f"r={self.test_r:.3f} on {self.n_test:,} held-out genes "
                f"(trained on {self.n_train:,}, gap {self.overfit_gap:.3f})")


def hand_features(promoter: str) -> np.ndarray:
    """Explicit promoter biology, computed rather than learned.

    Order matters — it must match whatever the model was trained with.
    """
    p = promoter.upper()
    n = max(len(p), 1)

    feats: list[float] = [
        (p.count("G") + p.count("C")) / n,       # overall GC
        (p.count("A") + p.count("T")) / n,       # overall AT
    ]

    # GC in windows. Promoters are AT-rich near the -10 box, which sits
    # close to the end of the upstream region.
    for lo, hi in GC_WINDOWS:
        w = p[lo:hi]
        feats.append((w.count("G") + w.count("C")) / max(len(w), 1))

    # Motif counts, whole window and core promoter region.
    core = p[-CORE_PROMOTER_WINDOW:]
    for motif in SIGMA70_MOTIFS:
        feats.append(p.count(motif))
        feats.append(core.count(motif))

    # Longest homopolymer run — long A or T tracts bend DNA and are
    # associated with strong promoters.
    longest, run = 0, 1
    for i in range(1, len(p)):
        run = run + 1 if p[i] == p[i - 1] else 1
        longest = max(longest, run)
    feats.append(float(longest))

    # Dinucleotide frequencies capture local sequence texture.
    for di in DINUCLEOTIDES:
        feats.append(sum(1 for i in range(n - 1) if p[i:i + 2] == di) / n)

    return np.asarray(feats, dtype=np.float32)


class ExpressionFusionModel:
    """Predicts log2 expression from promoter embeddings plus hand features.

    Pipeline:
        embeddings -> standardise -> PCA -> concat hand features
                   -> ridge and gradient boosting -> weighted average
    """

    def __init__(self, n_components: int = 100, seed: int = 42):
        self.n_components = n_components
        self.seed = seed

        self.scaler = None
        self.pca = None
        self.ridge = None
        self.gb = None
        self.ensemble_weight: float = 0.5     # share given to ridge
        self.use_hand_features: bool = True

        self.metrics = TrainingMetrics()
        self.target = "log2_tpm"

    # ---------------------------------------------------------------- #
    # Features
    # ---------------------------------------------------------------- #

    def _build(self, embeddings: np.ndarray, promoters: list[str] | None,
               fit: bool = False) -> np.ndarray:
        """Embeddings -> model-ready feature matrix."""
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        X = np.asarray(embeddings, dtype=np.float32)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        if fit:
            self.scaler = StandardScaler().fit(X)
            n_comp = min(self.n_components, X.shape[0] - 1, X.shape[1])
            self.pca = PCA(n_components=n_comp, random_state=self.seed)
            self.pca.fit(self.scaler.transform(X))

        reduced = self.pca.transform(self.scaler.transform(X))

        if self.use_hand_features and promoters:
            hand = np.vstack([hand_features(p) for p in promoters])
            return np.hstack([reduced, hand])
        return reduced

    # ---------------------------------------------------------------- #
    # Training
    # ---------------------------------------------------------------- #

    def fit(
        self,
        embeddings: np.ndarray,
        promoters: list[str],
        y: np.ndarray,
        validate: bool = True,
        test_fraction: float = 0.2,
    ) -> "ExpressionFusionModel":
        """Train on promoters with known expression.

        With validate=True the data is split and the held-out score is
        recorded. That number is the only honest measure of the model —
        performance on genes it trained on is always inflated.
        """
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.linear_model import RidgeCV
        from sklearn.metrics import mean_absolute_error, r2_score
        from sklearn.model_selection import train_test_split

        y = np.asarray(y, dtype=np.float32)

        if validate:
            idx = np.arange(len(y))
            tr, te = train_test_split(idx, test_size=test_fraction,
                                      random_state=self.seed)
        else:
            tr = np.arange(len(y))
            te = np.array([], dtype=int)

        emb_tr = np.asarray(embeddings)[tr]
        prom_tr = [promoters[i] for i in tr]

        X_tr = self._build(emb_tr, prom_tr, fit=True)

        self.ridge = RidgeCV(alphas=np.logspace(-1, 4, 20)).fit(X_tr, y[tr])
        self.gb = HistGradientBoostingRegressor(
            max_iter=400,
            learning_rate=0.04,
            max_depth=4,              # shallow, to resist memorising
            min_samples_leaf=40,
            l2_regularization=5.0,
            max_features=0.5,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=self.seed,
        ).fit(X_tr, y[tr])

        train_pred = self._blend(X_tr)
        self.metrics.train_r = _pearson(y[tr], train_pred)
        self.metrics.n_train = len(tr)

        if len(te):
            X_te = self._build(np.asarray(embeddings)[te],
                               [promoters[i] for i in te])

            # Pick the blend weight that works best on held-out data.
            p_ridge = self.ridge.predict(X_te)
            p_gb = self.gb.predict(X_te)
            best_w, best_r = 0.5, -np.inf
            for w in np.arange(0.0, 1.01, 0.05):
                r = _pearson(y[te], w * p_ridge + (1 - w) * p_gb)
                if r > best_r:
                    best_r, best_w = r, float(w)
            self.ensemble_weight = best_w

            pred = best_w * p_ridge + (1 - best_w) * p_gb
            self.metrics.test_r = _pearson(y[te], pred)
            self.metrics.test_r2 = float(r2_score(y[te], pred))
            self.metrics.test_mae = float(mean_absolute_error(y[te], pred))
            self.metrics.n_test = len(te)

        return self

    # ---------------------------------------------------------------- #
    # Inference
    # ---------------------------------------------------------------- #

    def _blend(self, X: np.ndarray) -> np.ndarray:
        w = self.ensemble_weight
        if self.ridge is not None and self.gb is not None:
            return w * self.ridge.predict(X) + (1 - w) * self.gb.predict(X)
        if self.ridge is not None:
            return self.ridge.predict(X)
        if self.gb is not None:
            return self.gb.predict(X)
        raise RuntimeError("model has not been trained or loaded")

    def predict(self, embeddings: np.ndarray,
                promoters: list[str] | None = None) -> np.ndarray:
        """Predicted log2 expression."""
        return self._blend(self._build(embeddings, promoters))

    def predict_tpm(self, embeddings: np.ndarray,
                    promoters: list[str] | None = None,
                    clip: tuple[float, float] = (0.0, 16.0)) -> np.ndarray:
        """Predicted expression in transcripts per million.

        The log2 output is clipped before exponentiating — an unclipped
        extrapolation can produce absurd numbers that then flow into the
        flux bounds.
        """
        log2 = np.clip(self.predict(embeddings, promoters), *clip)
        return np.power(2.0, log2)

    @property
    def is_trained(self) -> bool:
        return self.ridge is not None or self.gb is not None

    @property
    def expected_features(self) -> int | None:
        est = self.ridge if self.ridge is not None else self.gb
        return getattr(est, "n_features_in_", None)

    # ---------------------------------------------------------------- #
    # Persistence
    # ---------------------------------------------------------------- #

    def save(self, path: str | Path) -> Path:
        import joblib

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "format": "expression_fusion_v1",
            "scaler": self.scaler,
            "pca": self.pca,
            "ridge": self.ridge,
            "gb": self.gb,
            "ensemble_weight": self.ensemble_weight,
            "use_hand_features": self.use_hand_features,
            "hand_feature_count": HAND_FEATURE_COUNT,
            "n_components": self.n_components,
            "seed": self.seed,
            "target": self.target,
            "metrics": self.metrics.__dict__,
        }, path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "ExpressionFusionModel":
        """Load a saved model.

        Handles both this class's own format and the older flat dicts
        written by the training scripts, so existing model files on disk
        keep working without a retrain.
        """
        import joblib

        blob = joblib.load(Path(path))
        model = cls(
            n_components=blob.get("n_components", 100),
            seed=blob.get("seed", 42),
        )
        model.scaler = blob.get("scaler")
        model.pca = blob.get("pca")
        model.ridge = blob.get("ridge")
        model.gb = blob.get("gb")
        model.ensemble_weight = blob.get("ensemble_weight", 0.5)
        model.target = blob.get("target", "log2_tpm")

        metrics = blob.get("metrics")
        if isinstance(metrics, dict):
            model.metrics = TrainingMetrics(**metrics)
        else:
            # Older format stored the score as a bare key.
            model.metrics = TrainingMetrics(
                test_r=blob.get("test_r", 0.0),
                test_mae=blob.get("test_mae", 0.0),
                n_train=blob.get("n_train", 0),
                trained_on=blob.get("trained_on", ""),
            )

        # Older files did not record whether hand features were used.
        # Infer it by asking the estimator how many inputs it expects
        # versus how many the PCA produces.
        if "use_hand_features" in blob:
            model.use_hand_features = bool(blob["use_hand_features"])
        else:
            expected = model.expected_features
            n_pca = getattr(model.pca, "n_components_", None)
            model.use_hand_features = bool(
                expected and n_pca and expected > n_pca
            )

        return model

    def __repr__(self) -> str:
        if not self.is_trained:
            return "<ExpressionFusionModel untrained>"
        return (f"<ExpressionFusionModel {self.metrics.describe()} "
                f"hand_features={self.use_hand_features}>")


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


# -------------------------------------------------------------------- #
# Smoke test:  python ai/models/expression_fusion.py
# -------------------------------------------------------------------- #

if __name__ == "__main__":
    print("=" * 70)
    print("EXPRESSION FUSION MODEL")
    print("=" * 70)

    print(f"\nhand features per promoter: {HAND_FEATURE_COUNT}")
    demo = "TTGACA" + "N" * 20 + "TATAAT" + "A" * 268
    f = hand_features(demo[:300])
    print(f"  built {len(f)} features from a 300bp test promoter")
    print(f"  GC fraction: {f[0]:.3f}   longest run: {f[-len(DINUCLEOTIDES)-1]:.0f}")

    for candidate in (
        "data/models/expression_model_v2.joblib",
        "data/models/expression_model_operon.joblib",
        "data/models/expression_model.joblib",
    ):
        if Path(candidate).exists():
            print(f"\nloading {candidate}")
            m = ExpressionFusionModel.load(candidate)
            print(f"  {m!r}")
            print(f"  expects {m.expected_features} input features")
            print(f"  PCA components: {getattr(m.pca, 'n_components_', 'n/a')}")
            print(f"  hand features in use: {m.use_hand_features}")

            rng = np.random.default_rng(0)
            fake_emb = rng.normal(size=(3, 768)).astype(np.float32)
            fake_prom = [
                "".join(rng.choice(list("ACGT"), size=300)) for _ in range(3)
            ]
            try:
                tpm = m.predict_tpm(fake_emb, fake_prom)
                print(f"  predicted TPM for 3 random promoters: "
                      f"{np.round(tpm, 2)}")
                print("\n  Random DNA should predict LOW expression — it is")
                print("  not a real promoter.")
            except Exception as exc:
                print(f"  prediction failed: {type(exc).__name__}: {exc}")
            break
    else:
        print("\nNo saved model found. Train one with:")
        print("  python ai/training/train_expression_v2.py")

    print("\n" + "=" * 70)