"""Expression fusion model that combines HyenaDNA + RBS + TF + environment.

Owned by: Keshav
Architecture: 3-layer MLP with residual connections
"""


class ExpressionFusionModel:
    """Fuses multiple signals into a relative expression prediction."""

    def __init__(self, model_path: str | None = None):
        self.model = None

    def load(self):
        """Load the trained fusion model."""
        raise NotImplementedError

    def predict(self, features: dict) -> float:
        """Predict relative expression from fused features."""
        raise NotImplementedError
