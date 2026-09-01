"""Main prediction interface — implements the ExpressionPredictor contract.

Owned by: Keshav
This is the file that Arpit's SimulationRunner calls.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from contracts.interfaces import (
    ExpressionPredictor,
    PredictionInput,
    PredictionOutput,
    GeneExpressionResult,
)


class EcoliExpressionPredictor:
    """Concrete implementation of ExpressionPredictor for E. coli.

    Combines HyenaDNA embeddings + RBS scores + TF activation + environment
    to predict relative gene expression levels.
    """

    def __init__(self, model_dir: str = "./data/models"):
        self.model_dir = model_dir
        self._ready = False

    def load_models(self):
        """Load all required ML models."""
        # TODO: Keshav implements
        # 1. Load HyenaDNA wrapper
        # 2. Load expression fusion model
        # 3. Set self._ready = True
        pass

    def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """Predict expression levels for all genes."""
        if not self._ready:
            # Return dummy predictions until models are trained
            dummy_results = [
                GeneExpressionResult(
                    gene_id=f"gene_{i}",
                    relative_expression=0.5,
                    confidence=0.0,
                )
                for i in range(len(input_data.gene_sequences))
            ]
            return PredictionOutput(
                results=dummy_results,
                model_version="dummy-0.0.0",
                metadata={"warning": "Models not loaded, returning dummy predictions"},
            )

        # TODO: Keshav implements real prediction pipeline
        raise NotImplementedError

    def is_ready(self) -> bool:
        """Check if models are loaded."""
        return self._ready
