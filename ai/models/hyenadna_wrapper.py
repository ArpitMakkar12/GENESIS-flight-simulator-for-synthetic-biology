"""HyenaDNA model wrapper for E. coli sequence encoding.

Owned by: Keshav
Paper: HyenaDNA (Nguyen et al., 2023) — Paper #26 in literature review
Repo: https://github.com/HazyResearch/hyena-dna
"""


class HyenaDNAWrapper:
    """Wraps the fine-tuned HyenaDNA model for E. coli sequence embedding."""

    def __init__(self, model_path: str | None = None):
        self.model = None
        self.model_path = model_path

    def load(self):
        """Load the fine-tuned HyenaDNA model."""
        # TODO: Keshav implements
        raise NotImplementedError

    def encode(self, dna_sequence: str) -> list[float]:
        """Generate embedding vector for a DNA sequence."""
        # TODO: Keshav implements
        raise NotImplementedError
