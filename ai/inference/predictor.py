"""Main prediction interface — implements the ExpressionPredictor contract.

Owned by: Keshav

STATUS: STUB IMPLEMENTATION
---------------------------
This returns placeholder predictions so the rest of the pipeline can be
built and tested end to end. It does NOT predict anything real yet.

Every result is flagged with:
    prediction_source = "stub"
    confidence        = 0.0

Real prediction arrives in two tracks:
    Track A ("lookup") — known genes/parts, answered from the database
    Track B ("model")  — novel sequences, answered by HyenaDNA + fusion head

The interface will not change when those land. Only the internals will.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from contracts.interfaces import (  # noqa: E402
    GeneExpressionResult,
    PredictionInput,
    PredictionOutput,
)

# --------------------------------------------------------------------------
# Stub constants — every one of these is fake and must be replaced
# --------------------------------------------------------------------------

# Fold-change vs reference conditions. 1.0 means "exactly as in the
# reference state", which is the only neutral claim a stub can honestly
# make. Anything else would silently bias the simulation.
STUB_RELATIVE_EXPRESSION = 1.0

# Placeholder absolute anchor in transcripts-per-million. Roughly the
# median for a moderately expressed E. coli gene. Supplied only so the
# simulator's unit conversion has a number to work with.
STUB_REFERENCE_TPM = 100.0

MIN_UPSTREAM_BP = 300           # contract requires 300bp upstream + CDS
VALID_BASES = set("ACGTN")

MODEL_VERSION = "stub-0.1.0"


class EcoliExpressionPredictor:
    """Concrete implementation of ExpressionPredictor for E. coli.

    Currently a stub. The public surface (predict / is_ready) is final —
    swapping in the real models will not change how callers use this.
    """

    def __init__(self, model_dir: str = "./data/models"):
        self.model_dir = model_dir
        self._models_loaded = False

    # ---------------------------------------------------------------- #
    # Model lifecycle
    # ---------------------------------------------------------------- #

    def load_models(self) -> None:
        """Load HyenaDNA and the expression fusion head.

        Not implemented yet. The stub serves requests without any models,
        so nothing calls this for now.
        """
        # TODO: load HyenaDNA wrapper from self.model_dir
        # TODO: load expression fusion head
        # TODO: set self._models_loaded = True
        pass

    def is_ready(self) -> bool:
        """Whether the predictor can serve requests.

        Deliberately returns True even in stub mode. The point of the stub
        is to unblock the pipeline — a predictor that reports "not ready"
        would leave the simulator with nothing to call.

        Check `prediction_source` on the results, or `metadata["stub"]`,
        to know whether predictions are real.
        """
        return True

    def uses_real_models(self) -> bool:
        """True only once trained models are actually loaded."""
        return self._models_loaded

    # ---------------------------------------------------------------- #
    # Validation
    # ---------------------------------------------------------------- #

    @staticmethod
    def _validate(input_data: PredictionInput) -> list[str]:
        """Check inputs and return a list of human-readable warnings.

        Warnings, not exceptions — a malformed gene shouldn't kill an
        entire simulation. Real problems surface as low confidence.
        """
        warnings: list[str] = []

        for gene_id, seq in zip(input_data.gene_ids, input_data.gene_sequences):
            if not seq:
                warnings.append(f"{gene_id}: empty sequence")
                continue

            bad = set(seq.upper()) - VALID_BASES
            if bad:
                warnings.append(
                    f"{gene_id}: non-DNA characters {sorted(bad)}"
                )

            if len(seq) <= MIN_UPSTREAM_BP:
                warnings.append(
                    f"{gene_id}: sequence is {len(seq)}bp, needs more than "
                    f"{MIN_UPSTREAM_BP}bp (300bp upstream + CDS)"
                )

        if input_data.oxygen not in {"aerobic", "microaerobic", "anaerobic"}:
            warnings.append(f"unknown oxygen level: {input_data.oxygen!r}")

        if not 0.0 <= input_data.ph <= 14.0:
            warnings.append(f"pH out of range: {input_data.ph}")

        if not -10.0 <= input_data.temperature <= 100.0:
            warnings.append(f"temperature out of range: {input_data.temperature}")

        return warnings

    # ---------------------------------------------------------------- #
    # Prediction
    # ---------------------------------------------------------------- #

    def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """Return one placeholder result per gene.

        Gene IDs are carried through from the input, so results always
        line up with what the caller asked about.
        """
        warnings = self._validate(input_data)

        results = [
            GeneExpressionResult(
                gene_id=gene_id,
                relative_expression=STUB_RELATIVE_EXPRESSION,
                confidence=0.0,
                prediction_source="stub",
                promoter_strength=None,
                rbs_score=None,
                reference_expression_tpm=STUB_REFERENCE_TPM,
            )
            for gene_id in input_data.gene_ids
        ]

        return PredictionOutput(
            results=results,
            model_version=MODEL_VERSION,
            metadata={
                "stub": True,
                "warning": (
                    "Placeholder predictions. No model is loaded — every gene "
                    "returns reference-level expression with zero confidence."
                ),
                "gene_count": len(results),
                "validation_warnings": warnings,
                "conditions": {
                    "temperature": input_data.temperature,
                    "ph": input_data.ph,
                    "oxygen": input_data.oxygen,
                    "carbon_source": input_data.carbon_source,
                    "nitrogen_source": input_data.nitrogen_source,
                },
                "active_tfs": sorted(
                    tf for tf, active in input_data.tf_activation.items() if active
                ),
            },
        )


# --------------------------------------------------------------------------
# Manual smoke test:  python ai/inference/predictor.py
# --------------------------------------------------------------------------

if __name__ == "__main__":
    predictor = EcoliExpressionPredictor()

    sample = PredictionInput(
        gene_ids=["b0344", "b3702"],
        gene_sequences=["ATGC" * 200, "GGCA" * 200],   # 800bp each
        tf_activation={"CRP": True, "LacI": False},
        temperature=37.0,
        ph=7.0,
    )

    output = predictor.predict(sample)

    print(f"ready:   {predictor.is_ready()}")
    print(f"real:    {predictor.uses_real_models()}")
    print(f"version: {output.model_version}")
    print()
    for r in output.results:
        print(
            f"  {r.gene_id}: expression={r.relative_expression} "
            f"confidence={r.confidence} source={r.prediction_source}"
        )
    print()
    print(f"warnings: {output.metadata['validation_warnings']}")
    print(f"active TFs: {output.metadata['active_tfs']}")