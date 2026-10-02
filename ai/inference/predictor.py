"""Expression predictor — the implementation Arpit's SimulationRunner calls.

Owned by: Keshav
Implements the ExpressionPredictor contract in contracts/interfaces.py.

HOW A PREDICTION IS MADE
------------------------
Three layers, in order:

    1. IDENTIFY     what gene is this?            -> SequenceMatcher
    2. BASELINE     how strong is it normally?    -> database, or the model
    3. TF SHIFT     what changed vs reference?    -> regulatory network

    relative_expression = adjusted / baseline

LAYER 1 — identification
    SequenceMatcher answers one of three ways:

        known_wildtype   the gene is ours and the sequence is unchanged
        known_variant    the gene is ours but someone edited it
        novel            we have never seen this

LAYER 2 — baseline
    Known genes use their measured PRECISE-1K expression. That is real
    experimental data and beats a model with held-out r = 0.378 every
    time. Only genuinely novel sequences go through HyenaDNA and the
    fusion model.

    This is why the system is accurate in practice despite a modest
    model: most input is a lookup, not a prediction.

LAYER 3 — environment
    The fusion model reads sequence only. Feed it the same DNA at 37C
    and 42C and it returns the same number — it has no idea what the
    temperature is.

    Environment sensitivity is not machine learning. It is a lookup in
    the 10,783 regulator-gene interactions in our database:

        42C   -> RpoH switches on -> every RpoH target rises
        no O2 -> FNR switches on  -> every FNR target rises

    Verified: dnaK and groEL rise 2x under heat shock, lacZ rises 2x on
    lactose, FNR targets fall 0.5x anaerobically.
"""

from __future__ import annotations

import math
import os
import sys
import time
from functools import lru_cache

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai.inference.env_conditioner import (  # noqa: E402
    Environment,
    REFERENCE_TF_STATE,
    tf_state_changes,
)
from ai.inference.sequence_matcher import (  # noqa: E402
    MatchType,
    SequenceMatcher,
    UPSTREAM_BP,
)
from ai.models.model_registry import get_registry  # noqa: E402
from contracts.interfaces import (  # noqa: E402
    GeneExpressionResult,
    PredictionInput,
    PredictionOutput,
)

MODEL_VERSION = "genesis-expression-1.0.0"

VALID_BASES = set("ACGTN")

# Median reference expression across E. coli. Used only when we have
# nothing better — an unknown gene the model could not score either.
MEDIAN_TPM = 38.9

# How hard one regulator pushes, in log2 units. 1.0 means a single
# activator switching on roughly doubles expression.
TF_EFFECT_LOG2 = 1.0

# Ceiling on combined effect: 2^4 = 16x either way. Without it, a gene
# with many regulators produces absurd fold-changes.
MAX_FOLD_LOG2 = 4.0

CONFIDENCE = {
    "lookup_wildtype": 0.85,   # measured value, sequence unchanged
    "lookup_variant": 0.50,    # we know the gene, not what the edit did
    "model": 0.35,             # matches held-out r = 0.378
    "fallback": 0.10,          # nothing worked, assuming median
}


# --------------------------------------------------------------------- #
# RBS scoring
# --------------------------------------------------------------------- #
#
# The contract declares rbs_score as "computed by AI layer, not
# user-supplied", so the predictor owes a value for it.
#
# The calculator itself lives in the backend tree, because that is where
# the rest of the services sit. That means the import has to work from
# two different places:
#
#     inside the backend container          app.services.rbs_calculator
#     running this file from the repo root  backend/ is not on the path
#
# It is loaded lazily and the outcome cached, so a run that never sees a
# usable sequence never pays for ViennaRNA, and a missing calculator is
# not retried once per gene.

_RBS_FN = None          # relative_rbs_score, once located
_RBS_TRIED = False      # whether we have already gone looking


def _rbs_fn():
    """Return relative_rbs_score, or None if the calculator is absent."""
    global _RBS_FN, _RBS_TRIED
    if _RBS_TRIED:
        return _RBS_FN
    _RBS_TRIED = True

    backend = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "backend")
    )
    if backend not in sys.path:
        sys.path.append(backend)

    try:
        from app.services.rbs_calculator import (  # type: ignore[import-not-found]
            relative_rbs_score,
        )
        _RBS_FN = relative_rbs_score
    except Exception:
        _RBS_FN = None      # degrade quietly; rbs_score stays None
    return _RBS_FN


# How much sequence around the start codon the calculation needs. The
# Shine-Dalgarno motif sits within roughly 20bp of the start codon; 50
# upstream leaves room for the standby-site term, and 100 downstream
# covers the mRNA folding window.
RBS_UPSTREAM = 50
RBS_DOWNSTREAM = 100

START_CODONS = ("ATG", "GTG", "TTG")

# Scoring one RBS costs about 5ms, because ViennaRNA has to fold the mRNA
# and then co-fold it with the 16S tail. That is cheap for a construct and
# ruinous for a genome: 1,500 genes would take roughly 7.9 seconds against
# a 2,000ms budget.
#
# Two guards. The cache makes a repeated window free, which matters because
# the same gene is re-simulated constantly as someone tries conditions. The
# cap draws a line between the two kinds of request: a construct simulation
# is a handful of genes with real DNA and wants RBS, while a genome-scale
# run passes hundreds of known genes to constrain the metabolic model and
# has no use for per-gene translation rates. Past the cap, rbs_score is
# None and the metadata says why, rather than quietly missing the budget.
RBS_MAX_GENES = 50
_RBS_CACHE_SIZE = 4096


@lru_cache(maxsize=_RBS_CACHE_SIZE)
def _rbs_cached(window: str, start: int) -> float | None:
    """Cached RBS score for one window. Keyed on the window, not the gene,
    so two genes sharing an RBS share the answer."""
    fn = _rbs_fn()
    if fn is None:
        return None
    try:
        return round(float(fn(window, start)), 4)
    except Exception:
        return None


def _rbs_for(seq: str) -> float | None:
    """Score the ribosome binding site, on a 0 to 1 scale.

    The contract guarantees each sequence is 300bp of upstream DNA
    followed by the coding sequence, so the start codon sits at index
    UPSTREAM_BP and the RBS is the stretch just in front of it.

    Returning None whenever that layout does not hold is deliberate. A
    rate computed from the wrong window looks exactly as plausible as a
    correct one, and a silent wrong number is worse than an honest gap.
    Known genes passed with an empty sequence land here too: there is no
    DNA to score, so None is the truthful answer.
    """
    fn = _rbs_fn()
    if fn is None or not seq or len(seq) < UPSTREAM_BP + 3:
        return None

    if seq[UPSTREAM_BP:UPSTREAM_BP + 3] not in START_CODONS:
        return None        # not contract layout — refuse to guess

    window = seq[
        max(0, UPSTREAM_BP - RBS_UPSTREAM):UPSTREAM_BP + RBS_DOWNSTREAM
    ]
    start_in_window = min(UPSTREAM_BP, RBS_UPSTREAM)

    return _rbs_cached(window, start_in_window)


class EcoliExpressionPredictor:
    """Predicts relative gene expression for E. coli.

    Loading is staged. The gene tables load on first use (about a
    second). The fusion model loads only when a novel sequence appears.
    HyenaDNA loads only when that model actually has to run. A
    simulation touching only known genes never pays for either.
    """

    def __init__(
        self,
        model_dir: str = "./data/models",
        database_url: str | None = None,
    ):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql://biosandbox:biosandbox@localhost:5432/biosandbox",
        )
        self.registry = get_registry(model_dir)
        self.matcher = SequenceMatcher(self.database_url)

        self._baseline_tpm: dict[str, float] = {}
        self._regulators: dict[str, list[tuple[str, str]]] = {}
        self._db_loaded = False
        self._last_model_error: str | None = None

    # ---------------------------------------------------------------- #
    # Loading
    # ---------------------------------------------------------------- #

    def _load_db(self) -> None:
        """Baselines and the regulatory network. Sequences live in the matcher."""
        if self._db_loaded:
            return

        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        with engine.connect() as conn:
            for tag, tpm in conn.execute(text(
                "SELECT locus_tag, reference_expression_tpm FROM genes "
                "WHERE reference_expression_tpm IS NOT NULL"
            )):
                self._baseline_tpm[tag.lower()] = float(tpm)

            for tag, tf, effect in conn.execute(text(
                "SELECT g.locus_tag, tf.name, gr.regulation_type "
                "FROM gene_regulations gr "
                "JOIN genes g ON gr.gene_id = g.id "
                "JOIN transcription_factors tf ON gr.tf_id = tf.id"
            )):
                self._regulators.setdefault(tag.lower(), []).append(
                    (tf, _normalise_effect(effect))
                )

        if not self.matcher.is_loaded:
            self.matcher.load()

        self._db_loaded = True

    def load_models(self, include_hyenadna: bool = False) -> dict:
        """Eagerly load everything. Call at server startup.

        HyenaDNA is excluded by default because it costs 15 to 30
        seconds and most simulations never need it. Pass True on a
        server that will see novel sequences.
        """
        self._load_db()
        loaded = self.registry.preload(include_hyenadna=include_hyenadna)
        loaded["database"] = self._db_loaded
        loaded["genes"] = len(self._baseline_tpm)
        return loaded

    def is_ready(self) -> bool:
        return True

    def uses_real_models(self) -> bool:
        return True

    # ---------------------------------------------------------------- #
    # Track B — novel sequences
    # ---------------------------------------------------------------- #

    def _predict_novel(self, promoter: str, full_sequence: str) -> float | None:
        """Predict absolute expression (TPM) from sequence alone."""
        model = self.registry.expression_model()
        if model is None or not promoter:
            return None

        try:
            hyena = self.registry.hyenadna()
            if hyena is None:
                return None

            cds_head = full_sequence[UPSTREAM_BP:UPSTREAM_BP + 100]
            emb = hyena.embed_gene(promoter + cds_head)

            tpm = model.predict_tpm(
                emb.concat().reshape(1, -1), [promoter]
            )
            return float(tpm[0])

        except Exception as exc:
            self._last_model_error = f"{type(exc).__name__}: {exc}"
            return None

    # ---------------------------------------------------------------- #
    # Layer 3 — environment
    # ---------------------------------------------------------------- #

    def _tf_fold_change(
        self, tag: str | None, changes: dict[str, str]
    ) -> tuple[float, list[str]]:
        """How much do the flipped regulators move this gene?

        Effects sum in log space and are damped by the square root of
        how many fired. Biological effects are sub-additive — three
        activators do not give three times the push of one.
        """
        if not tag or not changes:
            return 1.0, []

        regs = self._regulators.get(tag, [])
        if not regs:
            return 1.0, []

        # Regulator names are spelled inconsistently between sources.
        # RegulonDB, which PRECISE-1K's TRN is built from, writes "Crp"
        # and "Fnr"; our reference state writes "CRP" and "FNR", the way
        # the literature does. Matching those case-sensitively silently
        # threw away 482 Crp edges and 286 Fnr edges — 342 genes that
        # should respond to a condition change and did not.
        #
        # Those are the two worst regulators to lose. CRP is the master
        # carbon-source switch, so it carries the entire glucose-to-
        # lactose response; FNR is the master oxygen switch, so it
        # carries the anaerobic response. Before this, "anaerobic" was
        # running on ArcA alone.
        #
        # Match on lowercase so neither spelling can go missing again.
        flips = {name.lower(): d for name, d in changes.items()}

        # Matching case-insensitively creates a second problem to solve in
        # the same breath. Both seeders populate this table: seed_regulondb
        # inserts 38 hand-curated edges as "CRP", then seed_precise inserts
        # the TRN's names verbatim as "Crp". Those became two separate rows
        # in transcription_factors, so a gene can carry the same regulator
        # twice under different spellings. Counting both would inflate the
        # effect and, worse, inflate the sqrt(n) damping denominator.
        #
        # So collapse to one entry per regulator, preferring a usable
        # direction over an unknown one.
        # Keyed on the lowercase name, but the original spelling is kept so
        # the metadata still reads "LacI-" rather than "laci-".
        unique: dict[str, tuple[str, str]] = {}
        for tf, effect in regs:
            key = tf.lower()
            if key not in unique or (unique[key][1] == "?" and effect != "?"):
                unique[key] = (tf, effect)

        total = 0.0
        fired: list[str] = []

        for key, (tf, effect) in unique.items():
            direction = flips.get(key)
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
        return float(2 ** max(-MAX_FOLD_LOG2, min(damped, MAX_FOLD_LOG2))), fired

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
        rbs_scored = 0

        # See RBS_MAX_GENES. A genome-scale request skips RBS scoring rather
        # than spending 5ms per gene on a number it was not asking for.
        score_rbs = len(input_data.gene_ids) <= RBS_MAX_GENES

        # Only say so when it actually cost the caller something. The normal
        # genome-scale path passes ~1,500 known genes with empty sequences,
        # which have no RBS to score in the first place — warning there would
        # put a misleading line on every single simulation. Warn only when
        # real DNA was supplied and the cap is what stopped it being read.
        if not score_rbs and any(
            len(s or "") >= UPSTREAM_BP + 3 for s in input_data.gene_sequences
        ):
            warnings.append(
                f"{len(input_data.gene_ids)} genes requested, over the "
                f"{RBS_MAX_GENES}-gene limit for RBS scoring — rbs_score is "
                f"None for all of them. Translation rates are meant for "
                f"construct-scale requests."
            )

        for gene_id, sequence in zip(
            input_data.gene_ids, input_data.gene_sequences
        ):
            seq = (sequence or "").upper().strip()

            bad = set(seq) - VALID_BASES
            if bad:
                warnings.append(f"{gene_id}: non-DNA characters {sorted(bad)[:3]}")

            # ---- Layer 1: what gene is this? ----
            match = self.matcher.match(gene_id, seq)
            tag = match.locus_tag.lower() if match.locus_tag else None
            baseline = self._baseline_tpm.get(tag) if tag else None

            # ---- Layer 2: how strong is it normally? ----
            if baseline is not None:
                # Known gene. A measured value beats a model prediction
                # even when the promoter has been edited — "lacZ,
                # modified" is a better starting point than a guess.
                source = "lookup"
                confidence = CONFIDENCE[
                    "lookup_wildtype"
                    if match.match_type is MatchType.KNOWN_WILDTYPE
                    else "lookup_variant"
                ]
                counts["lookup"] += 1
            else:
                predicted = self._predict_novel(match.upstream or "", seq)
                if predicted is not None:
                    baseline = predicted
                    source = "model"
                    confidence = CONFIDENCE["model"]
                    counts["model"] += 1
                else:
                    baseline = MEDIAN_TPM
                    source = "fallback"
                    confidence = CONFIDENCE["fallback"]
                    counts["fallback"] += 1

            # ---- Layer 3: what changed? ----
            fold, _fired = self._tf_fold_change(tag, changes)

            # ---- Layer 4: how well does the ribosome start here? ----
            # Independent of everything above. Transcription decides how
            # much mRNA exists; this decides how much protein gets made
            # from it. None when there is no sequence to read.
            rbs = _rbs_for(seq) if score_rbs else None
            if rbs is not None:
                rbs_scored += 1

            results.append(GeneExpressionResult(
                gene_id=gene_id,
                relative_expression=round(fold, 4),
                confidence=confidence,
                prediction_source=source,
                promoter_strength=round(math.log2(max(baseline, 1.0)) / 15.0, 4),
                rbs_score=rbs,
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
                "genes_with_rbs_score": rbs_scored,
                "rbs_scoring_enabled": score_rbs,
                "validation_warnings": warnings,
                "compute_ms": round(elapsed_ms, 1),
                "model_error": self._last_model_error,
                "models": self.registry.versions(),
                "note": (
                    "relative_expression is fold-change vs reference "
                    "(37C, pH7, aerobic, glucose, ammonium). Environment "
                    "sensitivity comes from transcription factor state "
                    "changes, not from the sequence model."
                ),
            },
        )


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


# -------------------------------------------------------------------- #
# Smoke test:  python ai/inference/predictor.py
# -------------------------------------------------------------------- #

if __name__ == "__main__":
    predictor = EcoliExpressionPredictor()

    print("=" * 72)
    print("EXPRESSION PREDICTOR — smoke test")
    print("=" * 72)

    t0 = time.perf_counter()
    status = predictor.load_models()
    print(f"\nloaded in {time.perf_counter() - t0:.2f}s")
    print(f"  genes with baseline  : {status['genes']:,}")
    print(f"  genes with regulators: {len(predictor._regulators):,}")
    print(f"  sequence matcher     : {predictor.matcher.gene_count:,} genes")
    print(f"  expression model     : {status['expression']}")
    print(f"  hyenadna             : {status['hyenadna']} (lazy on purpose)")

    genes = ["b0344", "b0002", "b0014", "b4143", "b0720"]

    # Contract format: exactly 300bp upstream, then the CDS starting at ATG.
    # A realistic AT-rich upstream with a strong Shine-Dalgarno motif in the
    # last 12 bases, so rbs_score comes back populated instead of None.
    # "ACGT" * 200 would not — index 300 lands on "ACG", not a start codon,
    # and the predictor refuses to score a window it cannot locate.
    _UP = ("TTGACAATTAATCATCCGGCTCGTATAATGTGTGGAATTGTGAGCGGATAACAATTTCACACA"
           "GGAAACAGCTATGACCATGATTACGGATTCACTGGCCGTCGTTTTACAACGTCGTGACTGGGA"
           "AAACCCTGGCGTTACCCAACTTAATCGCCTTGCAGCACATCCCCCTTTCGCCAGCTGGCGTAA"
           "TAGCGAAGAGGCCCGCACCGATCGCCCTTCCCAACAGTTGCGCAGCCTGAATGGCGAATGGCG")
    _CDS = "ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA"
    _SEQ = (_UP * 3)[:288] + "AAAGAGGAGAAA" + _CDS      # 300bp + CDS
    assert _SEQ[300:303] == "ATG", "upstream must be exactly 300bp"
    seqs = [_SEQ] * len(genes)

    scenarios = {
        "reference":  (dict(REFERENCE_TF_STATE), 37.0, 7.0, "aerobic", "glucose"),
        "anaerobic":  ({**REFERENCE_TF_STATE, "FNR": True, "ArcA": True},
                       37.0, 7.0, "anaerobic", "glucose"),
        "heat shock": ({**REFERENCE_TF_STATE, "RpoH": True, "RpoS": True},
                       42.0, 7.0, "aerobic", "glucose"),
        "lactose":    ({**REFERENCE_TF_STATE, "LacI": False, "CRP": True},
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
        print(f"  {'gene':8} {'fold':>8} {'baseline TPM':>14} {'RBS':>7}  "
              f"{'conf':>5}  source")
        for r in out.results:
            rbs = f"{r.rbs_score:.4f}" if r.rbs_score is not None else "none"
            print(f"  {r.gene_id:8} {r.relative_expression:>8.3f} "
                  f"{r.reference_expression_tpm:>14,.1f} {rbs:>7}  "
                  f"{r.confidence:>5.2f}  {r.prediction_source}")
        print(f"  {out.metadata['compute_ms']}ms  "
              f"sources={out.metadata['genes_by_source']}  "
              f"rbs_scored={out.metadata['genes_with_rbs_score']}/{len(genes)}")

    print("\n" + "=" * 72)
    print("Expected: dnaK (b0014) and groEL (b4143) rise under heat shock;")
    print("lacZ (b0344) rises on lactose; b0720 falls anaerobically.")
    print("=" * 72)
