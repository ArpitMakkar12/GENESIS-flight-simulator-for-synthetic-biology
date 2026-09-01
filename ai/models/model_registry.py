"""Tracks versions and paths of all AI models.

Owned by: Keshav
"""


class ModelRegistry:
    """Central registry for all ML model versions and paths."""

    def __init__(self, model_dir: str = "./data/models"):
        self.model_dir = model_dir
        self.models: dict[str, dict] = {}

    def register(self, name: str, version: str, path: str):
        """Register a model with its version and path."""
        self.models[name] = {"version": version, "path": path}

    def get_version_info(self) -> dict:
        """Return version info for all registered models (for provenance)."""
        return {name: info["version"] for name, info in self.models.items()}
