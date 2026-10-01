"""Expression predictor — the real implementation.

Owned by: Keshav
Implements the ExpressionPredictor contract that Arpit's SimulationRunner calls.

HOW A PREDICTION IS MADE
------------------------
Three layers, in order:

    1. BASELINE      how strong is this gene normally?
                     known gene  -> look up its measured TPM (PRECISE-1K)
                     novel DNA   -> HyenaDNA + trained model

    2. TF SHIFT      which master regulators changed versus reference?
                     each flip pushes the gene up or down

    3. FOLD-CHANGE   relative_expression = adjusted / baseline

WHY LAYER 2 EXISTS
------------------
The trained model predicts expression from promoter sequence alone. It
has no idea what temperature it is — feed it the same DNA at 37C and
42C and it returns the same number.

Environment sensitivity is not a machine-learning problem. It is a
lookup in the 10,783 regulator-gene interactions already in our
database:

    42C  -> RpoH switches on -> every RpoH target goes up
    no O2 -> FNR switches on  -> every FNR target goes up

TWO TRACKS
----------
    Track A "lookup"  the gene is in our database and unmodified.
                      We use its measured expression. High confidence.

    Track B "model"   the sequence is novel or edited. The model
                      predicts it. Lower confidence (held-out r = 0.38).

Most real input is Track A, which is why the system is accurate in
practice despite a modest model score.
"""

from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai.inference.env_conditioner import (  # noqa: E402
    Environment,
    REFERENCE_TF_STATE,
    tf_state_changes,
)
from contracts.interfaces import (  # noqa: E402
    GeneExpressionResult,
    PredictionInput,
    PredictionOutput,
)

MODEL_VERSION = "genesis-expression-1.0.0"

DEFAULT_MODEL_DIR = "./data/models"
MODEL_FILENAMES = (
    "expression_model_v2.joblib",
    "expression_model_operon.joblib",
    "expression_model.joblib",
)

UPSTREAM_BP = 300
VALID_BASES = set("ACGTN")

# Median reference expression across E. coli, used when we have nothing
# better to anchor a novel sequence against.
MEDIAN_TPM = 38.9

# How hard one regulator pushes, in log2 units. 1.0 means a single
# activator switching on roughly doubles expression.
TF_EFFECT_LOG2 = 1.0

# Hard ceiling on the combined effect: 2^4 = 16x up or down. Without
# this, a gene with many regulators can produce absurd fold-changes.
MAX_FOLD_LOG2 = 4.0

CONFIDENCE = {
    "lookup_wildtype": 0.85,   # measured value, sequence unchanged
    "lookup_variant": 0.50,    # we know the gene, not what the edit did
    "model": 0.35,             # matches held-out r = 0.38
    "fallback": 0.10,          # nothing worked, returning reference level
}


class EcoliExpressionPredictor:
    """Predicts relative gene expression for E. coli.

    Loading is lazy and staged: the database tables load on first use
    (fast, ~1s), the trained model only when a novel sequence appears,
    and HyenaDNA only when that model actually needs to run.
    """

    def __init__(
        self,
        model_dir: str = DEFAULT_MODEL_DIR,
        database_url: str | None = None,
    ):
        self.model_dir = Path(model_dir)
        self.database_url = database_url or os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql://biosandbox:biosandbox@localhost:5432/biosandbox",
        )

        self._baseline_tpm: dict[str, float] = {}
        self._cds_by_tag: dict[str, str] = {}
        self._alias_to_tag: dict[str, str] = {}
        self._regulators: dict[str, list[tuple[str, str]]] = {}

        self._model = None
        self._hyena = None
        self._db_loaded = False
        self._model_missing = False
        self._last_model_error: str | None = None

    # ---------------------------------------------------------------- #
    # Loading
    # ---------------------------------------------------------------- #

    def _load_db(self) -> None:
        """Pull the gene table and regulatory network into memory."""
        if self._db_loaded:
            return

        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        with engine.connect() as conn:
            for tag, name, tpm, cds in conn.execute(text(
                "SELECT locus_tag, name, reference_expression_tpm, dna_sequence "
                "FROM genes"
            )):
                key = tag.lower()
                if tpm is not None:
                    self._baseline_tpm[key] = float(tpm)
                if cds:
                    self._cds_by_tag[key] = cds.upper()
                self._alias_to_tag[key] = key
                if name:
                    self._alias_to_tag[name.lower()] = key

            for tag, tf, effect in conn.execute(text(
                "SELECT g.locus_tag, tf.name, gr.regulation_type "
                "FROM gene_regulations gr "
                "JOIN genes g ON gr.gene_id = g.id "
                "JOIN transcription_factors tf ON gr.tf_id = tf.id"
            )):
                self._regulators.setdefault(tag.lower(), []).append(
                    (tf, _normalise_effect(effect))
                )

        self._db_loaded = True

    def _load_model(self):
        """Load the trained expression model, if one has been built."""
        if self._model is not None or self._model_missing:
            return self._model

        import joblib

        for fname in MODEL_FILENAMES:
            path = self.model_dir / fname
            if path.exists():
                self._model = joblib.load(path)
                return self._model

        self._model_missing = True
        return None

    def _load_hyena(self):
        """Load HyenaDNA. Slow (~15-30s), so only on first novel sequence."""
        if self._hyena is None:
            from ai.models.hyenadna_wrapper import HyenaDNAWrapper

            self._hyena = HyenaDNAWrapper()
            self._hyena.load()
        return self._hyena

    def load_models(self) -> None:
        """Eagerly load everything. Call at server startup to avoid a
        slow first request."""
        self._load_db()
        self._load_model()

    def is_ready(self) -> bool:
        return True

    def uses_real_models(self) -> bool:
        return True

    # ---------------------------------------------------------------- #
    # Track A — known genes
    # ---------------------------------------------------------------- #

    def _resolve(self, gene_id: str) -> str | None:
        """Map a gene id or name onto a locus tag we know."""
        return self._alias_to_tag.get((gene_id or "").lower().strip())

    def _sequence_matches(self, tag: str, sequence: str) -> bool | None:
        """Is the supplied CDS identical to wild-type?

        Returns None when we cannot tell (no stored sequence, or the
        input is too short to contain a CDS).
        """
        stored = self._cds_by_tag.get(tag)
        if not stored or not sequence:
            return None

        seq = sequence.upper().strip()
        cds = seq[UPSTREAM_BP:] if len(seq) > UPSTREAM_BP else seq
        if not cds:
            return None
        return cds == stored

    # ---------------------------------------------------------------- #
    # Track B — novel sequences
    # ---------------------------------------------------------------- #

    def _predict_novel(self, sequence: str) -> float | None:
        """Predict absolute expression (TPM) from sequence alone."""
        model = self._load_model()
        if model is None:
            return None

        seq = sequence.upper().strip()
        if len(seq) <= UPSTREAM_BP:
            return None

        promoter = seq[:UPSTREAM_BP]
        cds_head = seq[UPSTREAM_BP:UPSTREAM_BP + 100]

        try:
            import numpy as np

            emb = self._load_hyena().embed_gene(promoter + cds_head)
            x_emb = emb.concat().reshape(1, -1).astype(np.float32)

            scaler = model.get("scaler")
            pca = model.get("pca")
            if scaler is None or pca is None:
                return None

            # v2 layout: PCA over embeddings, hand features appended after.
            x = pca.transform(scaler.transform(x_emb))

            # Work out whether the model was trained with hand features
            # appended, by asking it how many inputs it expects.
            estimator = model.get("ridge") or model.get("gb")
            expected = getattr(estimator, "n_features_in_", x.shape[1])
            if expected > x.shape[1]:
                x = np.hstack([x, _hand_features(promoter).reshape(1, -1)])

            ridge, gb = model.get("ridge"), model.get("gb")
            w = model.get("ensemble_weight", 0.5)

            if ridge is not None and gb is not None:
                log2_tpm = w * ridge.predict(x)[0] + (1 - w) * gb.predict(x)[0]
            elif ridge is not None:
                log2_tpm = ridge.predict(x)[0]
            elif gb is not None:
                log2_tpm = gb.predict(x)[0]
            else:
                return None

            return float(2 ** max(0.0, min(log2_tpm, 16.0)))

        except Exception as exc:
            self._last_model_error = f"{type(exc).__name__}: {exc}"
            return None

    # ---------------------------------------------------------------- #
    # Layer 2 — environment
    # ---------------------------------------------------------------- #

    def _tf_fold_change(
        self, tag: str | None, changes: dict[str, str]
    ) -> tuple[float, list[str]]:
        """How much do the flipped regulators move this gene?

        Effects are summed in log space and damped by the square root of
        how many fired — biological effects are sub-additive, so three
        activators do not give three times the push of one.
        """
        if not tag or not changes:
            return 1.0, []

        regs = self._regulators.get(tag, [])
        if not regs:
            return 1.0, []

        total = 0.0
        fired: list[str] = []

        for tf, effect in regs:
            direction = changes.get(tf)
            if direction is None or effect == "?":
                continue

            turned_on = direction == "on"
            if effect == "+":       # activator
                delta = TF_EFFECT_LOG2 if turned_on else -TF_EFFECT_LOG2
            else:                    # repressor
                delta = -TF_EFFECT_LOG2 if turned_on else TF_EFFECT_LOG2

            total += delta
            fired.append(f"{tf}{'+' if delta > 0 else '-'}")

        if not fired:
            return 1.0, []

        damped = total / math.sqrt(len(fired))
        clipped = max(-MAX_FOLD_LOG2, min(damped, MAX_FOLD_LOG2))
        return float(2 ** clipped), fired

    # ---------------------------------------------------------------- #
    # The contract
    # ---------------------------------------------------------------- #

    def predict(self, input_data: PredictionInput) -> PredictionOutput:
        started = time.perf_counter()
        self._load_db()

        env = Environment(
            temperature=input_data.temperature,
            ph=input_data.ph,
            oxygen=input_data.oxygen,
            carbon_source=input_data.carbon_source,
            nitrogen_source=input_data.nitrogen_source,
        )
        changes = tf_state_changes(input_data.tf_activation or {})

        results: list[GeneExpressionResult] = []
        counts = {"lookup": 0, "model": 0, "fallback": 0}
        warnings: list[str] = []

        for gene_id, sequence in zip(
            input_data.gene_ids, input_data.gene_sequences
        ):
            seq = (sequence or "").upper().strip()
            bad = set(seq) - VALID_BASES
            if bad:
                warnings.append(f"{gene_id}: non-DNA characters {sorted(bad)[:3]}")

            tag = self._resolve(gene_id)
            baseline = self._baseline_tpm.get(tag) if tag else None
            identical = self._sequence_matches(tag, seq) if tag else None

            # ---- Track A: known gene ----
            if baseline is not None:
                source = "lookup"
                confidence = CONFIDENCE[
                    "lookup_wildtype" if identical else "lookup_variant"
                ]
                counts["lookup"] += 1

            # ---- Track B: novel or edited sequence ----
            else:
                predicted = self._predict_novel(seq)
                if predicted is not None:
                    baseline = predicted
                    source = "model"
                    confidence = CONFIDENCE["model"]
                    counts["model"] += 1
                else:
                    baseline = baseline or MEDIAN_TPM
                    source = "fallback"
                    confidence = CONFIDENCE["fallback"]
                    counts["fallback"] += 1

            fold, fired = self._tf_fold_change(tag, changes)

            results.append(GeneExpressionResult(
                gene_id=gene_id,
                relative_expression=round(fold, 4),
                confidence=confidence,
                prediction_source=source,
                promoter_strength=round(math.log2(max(baseline, 1.0)) / 15.0, 4),
                rbs_score=None,
                reference_expression_tpm=round(baseline, 2),
            ))

        elapsed_ms = (time.perf_counter() - started) * 1000

        return PredictionOutput(
            results=results,
            model_version=MODEL_VERSION,
            metadata={
                "stub": False,
                "conditions": env.describe(),
                "is_reference_condition": env.is_reference,
                "tf_state_changes": changes,
                "genes_by_source": counts,
                "validation_warnings": warnings,
                "compute_ms": round(elapsed_ms, 1),
                "model_loaded": self._model is not None,
                "model_error": self._last_model_error,
                "note": (
                    "relative_expression is fold-change vs reference "
                    "(37C, pH7, aerobic, glucose, ammonium). Environment "
                    "sensitivity comes from transcription factor state "
                    "changes, not from the sequence model."
                ),
            },
        )


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #

def _normalise_effect(raw: str | None) -> str:
    """Map whatever the database stores onto '+', '-' or '?'."""
    if not raw:
        return "?"
    r = str(raw).strip().lower()
    if r.startswith("a") or r == "+":
        return "+"
    if r.startswith("r") or r == "-":
        return "-"
    return "?"


_MOTIFS = ["TTGACA", "TATAAT", "TATGAT", "TGTATAAT", "AAAAA", "TTTTT", "GGGCGG"]


def _hand_features(promoter: str):
    """Same hand features the model was trained with. Order matters."""
    import numpy as np

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
    for m in _MOTIFS:
        feats.append(p.count(m))
        feats.append(tail.count(m))
    longest, run = 0, 1
    for i in range(1, len(p)):
        run = run + 1 if p[i] == p[i - 1] else 1
        longest = max(longest, run)
    feats.append(longest)
    for di in ("AA", "AT", "TA", "TT", "GC", "CG", "GG", "CC"):
        feats.append(sum(1 for i in range(n - 1) if p[i:i + 2] == di) / n)
    return np.array(feats, dtype=np.float32)


# -------------------------------------------------------------------- #
# Smoke test:  python ai/inference/predictor.py
# -------------------------------------------------------------------- #

if __name__ == "__main__":
    predictor = EcoliExpressionPredictor()

    print("=" * 70)
    print("EXPRESSION PREDICTOR — smoke test")
    print("=" * 70)

    t0 = time.perf_counter()
    predictor.load_models()
    print(f"\nloaded in {time.perf_counter() - t0:.2f}s")
    print(f"  genes with baseline : {len(predictor._baseline_tpm):,}")
    print(f"  genes with regulators: {len(predictor._regulators):,}")
    print(f"  trained model loaded : {predictor._model is not None}")

    genes = ["b0344", "b0002", "b0014", "b4143", "b0720"]
    seqs = ["ACGT" * 200] * len(genes)

    scenarios = {
        "reference":   (dict(REFERENCE_TF_STATE), 37.0, 7.0, "aerobic", "glucose"),
        "anaerobic":   ({**REFERENCE_TF_STATE, "FNR": True, "ArcA": True},
                        37.0, 7.0, "anaerobic", "glucose"),
        "heat shock":  ({**REFERENCE_TF_STATE, "RpoH": True, "RpoS": True},
                        42.0, 7.0, "aerobic", "glucose"),
        "lactose":     ({**REFERENCE_TF_STATE, "LacI": False, "CRP": True},
                        37.0, 7.0, "aerobic", "lactose"),
    }

    for label, (tfs, temp, ph, o2, carbon) in scenarios.items():
        out = predictor.predict(PredictionInput(
            gene_ids=genes,
            gene_sequences=seqs,
            tf_activation=tfs,
            temperature=temp, ph=ph, oxygen=o2,
            carbon_source=carbon, nitrogen_source="ammonium",
        ))

        print(f"\n{label.upper()}  ({out.metadata['conditions']})")
        print(f"  TF flips: {out.metadata['tf_state_changes'] or 'none'}")
        print(f"  {'gene':8} {'fold':>8} {'baseline TPM':>14}  source")
        for r in out.results:
            print(f"  {r.gene_id:8} {r.relative_expression:>8.3f} "
                  f"{r.reference_expression_tpm:>14,.1f}  {r.prediction_source}")
        print(f"  computed in {out.metadata['compute_ms']}ms")

    print("\n" + "=" * 70)
    print("If the fold column is identical across scenarios, the TF layer")
    print("is not firing and environment sensitivity is broken.")
    print("=" * 70)