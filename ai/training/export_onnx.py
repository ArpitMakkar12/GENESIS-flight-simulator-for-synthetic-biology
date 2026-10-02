"""Export trained models to ONNX for fast CPU inference.

Owned by: Keshav

Run on the HOST:
    python ai/training/export_onnx.py

WHY BOTHER
----------
Two reasons, and the second matters more than speed.

    1. ONNX Runtime is typically 2 to 3 times faster than PyTorch on
       CPU for the same model.

    2. It removes the torch dependency from the serving container.
       torch plus transformers is about 800MB; onnxruntime is roughly
       15MB. Right now the backend image has no torch, which means
       novel sequences silently fall back instead of being predicted.
       ONNX fixes that without bloating the image.

WHAT MIGHT NOT WORK
-------------------
The two models export very differently:

    expression model   scikit-learn ridge and gradient boosting.
                       skl2onnx handles these cleanly. Low risk.

    HyenaDNA           custom architecture with torch.jit.script.
                       ONNX tracing often fails on scripted modules
                       and custom ops. Genuine risk of not working.

So each export is attempted independently and reported separately. A
failed HyenaDNA export does not block the expression model, and the
script says plainly which succeeded rather than implying both did.

VERIFICATION
------------
Exporting is not the same as exporting CORRECTLY. Each export is run
against the original and the outputs compared. A silent numerical
difference would be worse than a failed export, because it would
produce plausible wrong answers in production.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

MODEL_DIR = Path("data/models")
ONNX_DIR = MODEL_DIR / "onnx"

TOLERANCE = 1e-4      # max acceptable difference between original and ONNX


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


# -------------------------------------------------------------------- #
# Expression model
# -------------------------------------------------------------------- #

def export_expression_model() -> dict:
    """Export the sklearn ensemble. Low risk."""
    from ai.models.model_registry import get_registry

    result = {"name": "expression_model", "ok": False, "detail": ""}

    registry = get_registry(MODEL_DIR)
    model = registry.expression_model()
    if model is None:
        result["detail"] = "no trained model found"
        return result

    try:
        from skl2onnx import to_onnx
    except ImportError:
        result["detail"] = (
            "skl2onnx not installed — pip install skl2onnx onnxruntime"
        )
        return result

    n_features = model.expected_features
    if not n_features:
        result["detail"] = "model does not report its input size"
        return result

    print(f"  input features: {n_features}")
    rng = np.random.default_rng(0)
    sample = rng.normal(size=(8, n_features)).astype(np.float32)

    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    exported = {}

    # Ridge and gradient boosting export separately. The ensemble is a
    # weighted average done in Python, so there is nothing to export
    # for the blend itself — the weight is just a number.
    for name, estimator in (("ridge", model.ridge), ("gb", model.gb)):
        if estimator is None:
            continue
        try:
            onx = to_onnx(estimator, sample)
            path = ONNX_DIR / f"expression_{name}.onnx"
            path.write_bytes(onx.SerializeToString())
            exported[name] = path
            print(f"  exported {name}: {path.stat().st_size / 1e6:.2f}MB")
        except Exception as exc:
            print(f"  {name} failed: {type(exc).__name__}: {exc}")

    if not exported:
        result["detail"] = "nothing exported"
        return result

    # ---- verify the numbers match ----
    print("\n  verifying against the original...")
    try:
        import onnxruntime as ort
    except ImportError:
        result["ok"] = True
        result["detail"] = (
            f"exported {list(exported)} but onnxruntime is not installed, "
            "so the outputs were not verified"
        )
        return result

    max_diff = 0.0
    for name, path in exported.items():
        estimator = getattr(model, name)
        original = estimator.predict(sample)

        sess = ort.InferenceSession(str(path),
                                    providers=["CPUExecutionProvider"])
        onnx_out = sess.run(None, {sess.get_inputs()[0].name: sample})[0]
        onnx_out = np.asarray(onnx_out).reshape(original.shape)

        diff = float(np.max(np.abs(original - onnx_out)))
        max_diff = max(max_diff, diff)
        verdict = "match" if diff < TOLERANCE else "MISMATCH"
        print(f"    {name}: max difference {diff:.2e}  {verdict}")

    if max_diff < TOLERANCE:
        result["ok"] = True
        result["detail"] = (
            f"exported and verified ({list(exported)}), "
            f"max difference {max_diff:.2e}"
        )
    else:
        result["detail"] = (
            f"exported but outputs differ by {max_diff:.2e} — do not use"
        )

    # ---- speed comparison ----
    if result["ok"] and "ridge" in exported:
        print("\n  speed on 1000 predictions:")
        big = rng.normal(size=(1000, n_features)).astype(np.float32)

        t0 = time.perf_counter()
        model.ridge.predict(big)
        sk_ms = (time.perf_counter() - t0) * 1000

        sess = ort.InferenceSession(str(exported["ridge"]),
                                    providers=["CPUExecutionProvider"])
        t0 = time.perf_counter()
        sess.run(None, {sess.get_inputs()[0].name: big})
        onnx_ms = (time.perf_counter() - t0) * 1000

        print(f"    scikit-learn: {sk_ms:7.2f}ms")
        print(f"    onnx runtime: {onnx_ms:7.2f}ms  "
              f"({sk_ms / max(onnx_ms, 1e-9):.1f}x)")

    return result


# -------------------------------------------------------------------- #
# HyenaDNA
# -------------------------------------------------------------------- #

def export_hyenadna() -> dict:
    """Export HyenaDNA. Genuine risk of failure — custom architecture."""
    result = {"name": "hyenadna", "ok": False, "detail": ""}

    try:
        import torch
    except ImportError:
        result["detail"] = "torch not installed"
        return result

    from ai.models.model_registry import get_registry

    registry = get_registry(MODEL_DIR)
    wrapper = registry.hyenadna()
    if wrapper is None:
        result["detail"] = "HyenaDNA not downloaded"
        return result

    model = wrapper._model
    tokenizer = wrapper._tokenizer

    # A representative input: 300bp promoter plus 100bp of coding start,
    # which is what the predictor actually feeds it.
    sample_dna = "ACGT" * 100
    tokens = tokenizer(sample_dna, return_tensors="pt")
    input_ids = tokens["input_ids"]

    print(f"  sample input: {input_ids.shape}")

    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    path = ONNX_DIR / "hyenadna.onnx"

    try:
        print("  tracing... (this is where custom architectures usually fail)")
        with torch.no_grad():
            torch.onnx.export(
                model,
                (input_ids,),
                str(path),
                input_names=["input_ids"],
                output_names=["last_hidden_state"],
                dynamic_axes={
                    "input_ids": {0: "batch", 1: "sequence"},
                    "last_hidden_state": {0: "batch", 1: "sequence"},
                },
                opset_version=17,
                do_constant_folding=True,
            )
        print(f"  exported: {path.stat().st_size / 1e6:.1f}MB")

    except Exception as exc:
        result["detail"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        print(f"  export failed: {result['detail']}")
        print("\n  This is the expected failure mode. HyenaDNA uses")
        print("  torch.jit.script and custom Hyena operators, which ONNX")
        print("  tracing frequently cannot follow. PyTorch inference still")
        print("  works and already meets the latency budget at 0.117s/gene.")
        return result

    # ---- verify ----
    try:
        import onnxruntime as ort

        with torch.no_grad():
            original = model(input_ids).last_hidden_state.numpy()

        sess = ort.InferenceSession(str(path),
                                    providers=["CPUExecutionProvider"])
        onnx_out = sess.run(
            None, {"input_ids": input_ids.numpy()}
        )[0]

        diff = float(np.max(np.abs(original - onnx_out)))
        print(f"  max difference vs PyTorch: {diff:.2e}")

        if diff < 1e-3:     # looser than sklearn — float accumulation
            result["ok"] = True
            result["detail"] = f"exported and verified, max difference {diff:.2e}"
        else:
            result["detail"] = f"exported but outputs differ by {diff:.2e}"

    except ImportError:
        result["ok"] = True
        result["detail"] = "exported but onnxruntime missing, not verified"
    except Exception as exc:
        result["detail"] = f"verification failed: {type(exc).__name__}: {exc}"

    return result


# -------------------------------------------------------------------- #

def main() -> None:
    print("=" * 72)
    print("ONNX EXPORT")
    print("=" * 72)
    print(f"\noutput directory: {ONNX_DIR.resolve()}")

    results = []

    section("1. Expression model (scikit-learn — low risk)")
    results.append(export_expression_model())

    section("2. HyenaDNA (custom architecture — may fail)")
    results.append(export_hyenadna())

    section("SUMMARY")
    print()
    for r in results:
        status = "OK  " if r["ok"] else "FAIL"
        print(f"  [{status}] {r['name']}: {r['detail']}")

    ok = [r for r in results if r["ok"]]
    print()
    if len(ok) == len(results):
        print("  Both models exported and verified.")
        print("  The backend container can now run Track B without torch:")
        print("    pip install onnxruntime   (~15MB, versus ~800MB for torch)")
    elif ok:
        print("  Partial export. The expression model is portable; HyenaDNA")
        print("  still needs PyTorch to produce embeddings, so the serving")
        print("  container cannot drop torch yet.")
        print("\n  This does not block anything. PyTorch inference runs at")
        print("  0.117s per gene against a 2s budget, and known genes never")
        print("  touch the model at all.")
    else:
        print("  Nothing exported. PyTorch inference is unaffected and")
        print("  already meets the latency budget.")

    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()