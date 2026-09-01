"""Interface contracts between backend (Arpit) and AI module (Keshav).

This file is SHARED — changes require agreement from both team members.
Arpit's simulation_runner.py imports ExpressionPredictor from here.
Keshav's ai/inference/predictor.py implements ExpressionPredictor.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class GeneExpressionResult:
    """Prediction result for a single gene."""
    gene_id: str
    relative_expression: float  # 0.0 to 1.0 (normalized)
    confidence: float           # 0.0 to 1.0
    promoter_strength: float | None = None
    rbs_score: float | None = None


@dataclass
class PredictionInput:
    """Input to the expression prediction engine."""
    gene_sequences: list[str]                # DNA sequences per gene
    rbs_scores: list[float]                  # RBS Calculator TIR scores
    tf_activation: dict[str, bool]           # {TF_name: is_active}
    temperature: float = 37.0                # Celsius
    ph: float = 7.0
    oxygen: str = "aerobic"                  # aerobic/microaerobic/anaerobic
    carbon_source: str = "glucose"
    nitrogen_source: str = "ammonium"


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
        """Predict expression levels for all genes in the input."""
        ...

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready for inference."""
        ...
