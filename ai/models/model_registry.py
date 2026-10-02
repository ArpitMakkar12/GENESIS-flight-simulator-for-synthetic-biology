"""Model registry — finds, loads and caches the AI layer's models.

Owned by: Keshav

WHAT THIS IS
------------
One place that knows where models live, which versions exist, and how
to load them. Without it, every caller hardcodes file paths and reloads
the same 16MB model repeatedly.

WHY IT MATTERS HERE
-------------------
Loading is expensive and uneven:

    expression model   ~1.8MB joblib    under a second
    HyenaDNA           16MB + torch     15 to 30 seconds

HyenaDNA is the one that hurts. Loading it inside a web request would
blow the 2 second budget on the first call every time the server
restarts. So the registry caches aggressively and lets the server
preload at startup instead.

It is also the honest answer to "which model produced this number" —
every loaded model reports its file, size, and held-out score, and that
goes into the simulation metadata.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

DEFAULT_MODEL_DIR = Path(
    os.getenv("MODEL_DIR", "./data/models")
)

# Checked in order — the first that exists wins. v2 is the current best
# (held-out r = 0.378); the others are earlier experiments kept so an
# older model file still loads rather than erroring.
EXPRESSION_MODEL_CANDIDATES = (
    "expression_model_v2.joblib",
    "expression_model_operon.joblib",
    "expression_model.joblib",
)

HYENADNA_DIR = "hyenadna-32k"


@dataclass
class ModelInfo:
    """What we know about one model file on disk."""
    name: str
    path: Path
    exists: bool
    size_mb: float = 0.0
    modified: str = ""
    detail: str = ""

    def describe(self) -> str:
        if not self.exists:
            return f"{self.name}: MISSING ({self.path})"
        extra = f" — {self.detail}" if self.detail else ""
        return (f"{self.name}: {self.size_mb:.1f}MB, "
                f"modified {self.modified}{extra}")


class ModelRegistry:
    """Loads models once and hands out the same instance thereafter.

    Deliberately lazy: nothing is read from disk until something asks
    for it. A simulation that only touches known genes never loads
    HyenaDNA at all, which is why the common path is sub-millisecond.
    """

    def __init__(self, model_dir: str | Path = DEFAULT_MODEL_DIR):
        self.model_dir = Path(model_dir)
        self._expression = None
        self._hyenadna = None
        self._expression_path: Path | None = None

    # ---------------------------------------------------------------- #
    # Discovery
    # ---------------------------------------------------------------- #

    def _stat(self, name: str, path: Path, detail: str = "") -> ModelInfo:
        if not path.exists():
            return ModelInfo(name=name, path=path, exists=False)

        if path.is_dir():
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        else:
            size = path.stat().st_size

        return ModelInfo(
            name=name,
            path=path,
            exists=True,
            size_mb=size / 1e6,
            modified=datetime.fromtimestamp(
                path.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M"),
            detail=detail,
        )

    def find_expression_model(self) -> Path | None:
        """First expression model file that actually exists."""
        for name in EXPRESSION_MODEL_CANDIDATES:
            path = self.model_dir / name
            if path.exists():
                return path
        return None

    def available(self) -> list[ModelInfo]:
        """Everything the registry can see, loaded or not."""
        infos: list[ModelInfo] = []

        expr = self.find_expression_model()
        if expr:
            detail = ""
            try:
                from ai.models.expression_fusion import ExpressionFusionModel

                m = self._expression or ExpressionFusionModel.load(expr)
                detail = f"held-out r={m.metrics.test_r:.3f}"
            except Exception:
                detail = "could not read metrics"
            infos.append(self._stat("expression_fusion", expr, detail))
        else:
            infos.append(
                ModelInfo("expression_fusion",
                          self.model_dir / EXPRESSION_MODEL_CANDIDATES[0],
                          exists=False)
            )

        infos.append(self._stat(
            "hyenadna", self.model_dir / HYENADNA_DIR,
            "1.6M params, 256-dim embeddings",
        ))

        return infos

    # ---------------------------------------------------------------- #
    # Loading
    # ---------------------------------------------------------------- #

    def expression_model(self, required: bool = False):
        """The trained expression predictor, or None if there isn't one.

        Returns None rather than raising by default — the pipeline can
        still answer from database lookups without a trained model, and
        a missing model should degrade rather than break a simulation.
        """
        if self._expression is not None:
            return self._expression

        path = self.find_expression_model()
        if path is None:
            if required:
                raise FileNotFoundError(
                    f"No expression model in {self.model_dir.resolve()}.\n"
                    "Train one with:\n"
                    "  python ai/training/train_expression_v2.py"
                )
            return None

        from ai.models.expression_fusion import ExpressionFusionModel

        self._expression = ExpressionFusionModel.load(path)
        self._expression_path = path
        return self._expression

    def hyenadna(self, required: bool = False):
        """The DNA encoder. Slow to load, so only call when needed."""
        if self._hyenadna is not None:
            return self._hyenadna

        path = self.model_dir / HYENADNA_DIR
        if not path.exists():
            if required:
                raise FileNotFoundError(
                    f"No HyenaDNA at {path.resolve()}.\n"
                    "Download it with:\n"
                    '  python -c "from huggingface_hub import snapshot_download; '
                    "snapshot_download('LongSafari/hyenadna-small-32k-seqlen-hf', "
                    f"local_dir='{path}')\""
                )
            return None

        from ai.models.hyenadna_wrapper import HyenaDNAWrapper

        wrapper = HyenaDNAWrapper(str(path))
        wrapper.load()
        self._hyenadna = wrapper
        return wrapper

    def preload(self, include_hyenadna: bool = True) -> dict[str, bool]:
        """Load everything up front.

        Call this at server startup. HyenaDNA takes 15 to 30 seconds, and
        paying that during a user's first simulation would blow the
        latency budget.
        """
        loaded = {"expression": False, "hyenadna": False}

        try:
            loaded["expression"] = self.expression_model() is not None
        except Exception:
            pass

        if include_hyenadna:
            try:
                loaded["hyenadna"] = self.hyenadna() is not None
            except Exception:
                pass

        return loaded

    # ---------------------------------------------------------------- #
    # Provenance
    # ---------------------------------------------------------------- #

    def versions(self) -> dict[str, str]:
        """What went into a prediction. Goes into simulation metadata."""
        out: dict[str, str] = {}

        if self._expression is not None:
            r = self._expression.metrics.test_r
            name = self._expression_path.name if self._expression_path else "?"
            out["expression_fusion"] = f"{name} (r={r:.3f})"
        else:
            path = self.find_expression_model()
            out["expression_fusion"] = path.name if path else "not loaded"

        out["hyenadna"] = (
            "hyenadna-small-32k-seqlen (loaded)" if self._hyenadna is not None
            else "hyenadna-small-32k-seqlen (not loaded)"
        )
        return out

    def clear(self) -> None:
        """Drop cached models. Useful after retraining."""
        self._expression = None
        self._hyenadna = None
        self._expression_path = None

    def __repr__(self) -> str:
        return (f"<ModelRegistry {self.model_dir} "
                f"expression={'loaded' if self._expression else 'lazy'} "
                f"hyenadna={'loaded' if self._hyenadna else 'lazy'}>")


# A shared instance, so separate callers do not each load their own copy
# of a 16MB model.
_registry: ModelRegistry | None = None


def get_registry(model_dir: str | Path | None = None) -> ModelRegistry:
    global _registry
    if _registry is None or model_dir is not None:
        _registry = ModelRegistry(model_dir or DEFAULT_MODEL_DIR)
    return _registry


# -------------------------------------------------------------------- #
# Smoke test:  python ai/models/model_registry.py
# -------------------------------------------------------------------- #

if __name__ == "__main__":
    import time

    print("=" * 70)
    print("MODEL REGISTRY")
    print("=" * 70)

    reg = get_registry()
    print(f"\nmodel directory: {reg.model_dir.resolve()}\n")

    for info in reg.available():
        print(f"  {info.describe()}")

    print("\n" + "-" * 70)
    print("Loading the expression model")
    print("-" * 70)

    t0 = time.perf_counter()
    model = reg.expression_model()
    if model:
        print(f"  loaded in {time.perf_counter() - t0:.2f}s")
        print(f"  {model!r}")
    else:
        print("  none found — train one first")

    print("\n  loading again (should be instant — cached)")
    t0 = time.perf_counter()
    reg.expression_model()
    print(f"  {(time.perf_counter() - t0) * 1000:.3f}ms")

    print("\n" + "-" * 70)
    print("HyenaDNA is NOT loaded here on purpose")
    print("-" * 70)
    print("  It costs 15 to 30 seconds. A simulation that only touches")
    print("  known genes never needs it, so the registry leaves it alone")
    print("  until something actually asks for an embedding.")

    print("\n" + "-" * 70)
    print("Provenance reported into simulation metadata")
    print("-" * 70)
    for k, v in reg.versions().items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 70)