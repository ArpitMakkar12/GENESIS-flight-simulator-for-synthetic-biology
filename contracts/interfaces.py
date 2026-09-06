"""Interface contracts between backend (Arpit) and AI module (Keshav).

This file is SHARED — changes require agreement from both team members.
Arpit's simulation_runner.py imports ExpressionPredictor from here.
Keshav's ai/inference/predictor.py implements ExpressionPredictor.

=== SEQUENCE FORMAT ===
Each entry in gene_sequences must include 300bp UPSTREAM of the CDS
(the promoter region) followed by the full coding sequence.
Format: [300bp upstream + CDS]
Without the upstream region, promoter strength cannot be predicted.

=== EXPRESSION UNITS ===
relative_expression is normalised to the REFERENCE condition
(37°C, pH 7.0, aerobic, glucose, ammonium).

A value of 1.0 means "same expression as this gene under reference
conditions". A value of 2.0 means double. This is NOT capped at 1.0.

The reference_expression_tpm field gives the absolute anchor:
transcripts-per-million under reference conditions, sourced from
published RNA-seq. The simulator uses:

    enzyme_concentration ∝ relative_expression × reference_expression_tpm

This gives proper units for flux = concentration × kcat.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class GeneExpressionResult:
    """Prediction result for a single gene."""
    gene_id: str
    relative_expression: float      # fold-change vs reference condition (1.0 = reference)
    confidence: float               # 0.0 to 1.0
    prediction_source: str = ""     # "lookup" (Track A) or "model" (Track B)
    promoter_strength: float | None = None
    rbs_score: float | None = None  # computed by AI layer, not user-supplied
    reference_expression_tpm: float | None = None  # absolute anchor (TPM)


@dataclass
class PredictionInput:
    """Input to the expression prediction engine.

    gene_ids and gene_sequences are parallel lists — gene_ids[i]
    corresponds to gene_sequences[i]. This is enforced by validation.
    """
    gene_ids: list[str]                      # locus tags or part names (e.g. ["b0344", "BBa_J23100"])
    gene_sequences: list[str]                # DNA: 300bp upstream + CDS per gene
    tf_activation: dict[str, bool]           # {TF_name: is_active}
    temperature: float = 37.0                # Celsius
    ph: float = 7.0
    oxygen: str = "aerobic"                  # aerobic / microaerobic / anaerobic
    carbon_source: str = "glucose"
    nitrogen_source: str = "ammonium"

    def __post_init__(self):
        if len(self.gene_ids) != len(self.gene_sequences):
            raise ValueError(
                f"gene_ids ({len(self.gene_ids)}) and gene_sequences "
                f"({len(self.gene_sequences)}) must have the same length"
            )


@dataclass
class PredictionOutput:
    """Output from the expression prediction engine."""
    results: list[GeneExpressionResult]
    model_version: str = "0.1.0"
    metadata: dict = field(default_factory=dict)


class ExpressionPredictor(Protocol):
    """Protocol that Keshav's AI module must implement.

    Arpit's SimulationRunner calls this interface.
    Keshav's ai/inference/predictor.py provides the implementation.
    """

    def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """Predict expression levels for all genes in the input.

        For known genes (Track A): returns lookup-based predictions
        with high confidence.
        For novel sequences (Track B): returns model-based predictions
        with lower confidence.
        """
        ...

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready for inference."""
        ...
