"""End-to-end preset test — does each growth condition give a different answer?

Owned by: Keshav

Run on the HOST with the stack up:
    python tests/test_presets.py

WHAT THIS CHECKS
----------------
The five presets in frontend/src/lib/presets.ts are what users will
actually click. This hits the real API with each one and confirms:

    1. the simulation returns a growth rate
    2. the growth rates DIFFER between conditions
    3. expression predictions differ between conditions
    4. every response comes back under the 2 second budget

If every preset returns the same growth rate, the pipeline is ignoring
the environment and something upstream is broken.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

API = "http://localhost:8000/api/v1/simulate"

# Mirrors frontend/src/lib/presets.ts
PRESETS = {
    "reference": dict(temperature=37.0, ph=7.0, oxygen_level="aerobic",
                      carbon_source="glucose", nitrogen_source="ammonium"),
    "anaerobic": dict(temperature=37.0, ph=7.0, oxygen_level="anaerobic",
                      carbon_source="glucose", nitrogen_source="ammonium"),
    "heat_shock": dict(temperature=42.0, ph=7.0, oxygen_level="aerobic",
                       carbon_source="glucose", nitrogen_source="ammonium"),
    "acid_stress": dict(temperature=37.0, ph=5.5, oxygen_level="aerobic",
                        carbon_source="glycerol", nitrogen_source="ammonium"),
    "glycerol_feed": dict(temperature=37.0, ph=7.0, oxygen_level="aerobic",
                          carbon_source="glycerol", nitrogen_source="ammonium"),
}

BUDGET_MS = 2000


def call(payload: dict) -> tuple[dict | None, float, str | None]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        return data, (time.perf_counter() - t0) * 1000, None
    except urllib.error.HTTPError as e:
        return None, (time.perf_counter() - t0) * 1000, f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}"
    except Exception as e:
        return None, (time.perf_counter() - t0) * 1000, f"{type(e).__name__}: {e}"


def main() -> None:
    print("=" * 78)
    print("PRESET END-TO-END TEST")
    print("=" * 78)
    print(f"\nPOST {API}\n")

    results: dict[str, dict] = {}

    header = f"{'preset':15} {'growth':>9} {'doubling':>9} {'viability':>10} {'wall ms':>9} {'server ms':>10}"
    print(header)
    print("-" * len(header))

    for name, params in PRESETS.items():
        data, wall_ms, err = call(params)

        if err:
            print(f"{name:15}  FAILED  {err}")
            continue

        results[name] = data
        print(f"{name:15} "
              f"{data.get('growth_rate', 0):>9.4f} "
              f"{data.get('doubling_time', 0):>9.2f} "
              f"{data.get('viability_score', 0):>10.3f} "
              f"{wall_ms:>9.0f} "
              f"{data.get('compute_time_ms', 0):>10.0f}")

    if len(results) < 2:
        print("\nToo few successful runs to compare. Is the stack running?")
        return

    # ---------------------------------------------------------------- #
    print("\n" + "=" * 78)
    print("CHECK 1 — do the growth rates actually differ?")
    print("=" * 78)

    rates = {k: v.get("growth_rate", 0) for k, v in results.items()}
    spread = max(rates.values()) - min(rates.values())
    print(f"\n  range: {min(rates.values()):.4f} to {max(rates.values()):.4f}")
    print(f"  spread: {spread:.4f}")

    if spread < 1e-4:
        print("\n  FAIL — every condition gives the same growth rate.")
        print("  The pipeline is ignoring the environment entirely.")
    else:
        print("\n  PASS — conditions produce different growth rates.")
        ref = rates.get("reference")
        if ref:
            for k, v in sorted(rates.items(), key=lambda x: -x[1]):
                print(f"    {k:15} {v:.4f}  ({v/ref:.2f}x reference)")

    # ---------------------------------------------------------------- #
    print("\n" + "=" * 78)
    print("CHECK 2 — do the expression predictions differ?")
    print("=" * 78)

    def profile(data):
        preds = data.get("expression_predictions") or []
        return {p.get("gene_id"): round(p.get("relative_expression", 0), 4)
                for p in preds}

    ref_profile = profile(results.get("reference", {}))
    if not ref_profile:
        print("\n  No expression_predictions in the response.")
    else:
        print(f"\n  reference profile: {ref_profile}\n")
        any_diff = False
        for name, data in results.items():
            if name == "reference":
                continue
            p = profile(data)
            changed = {g: (ref_profile.get(g), v)
                       for g, v in p.items() if ref_profile.get(g) != v}
            if changed:
                any_diff = True
                print(f"  {name}:")
                for g, (was, now) in changed.items():
                    print(f"    {g}  {was} -> {now}")
            else:
                print(f"  {name}: identical to reference")

        print()
        if any_diff:
            print("  PASS — expression responds to the environment.")
        else:
            print("  WARNING — expression is identical across all conditions.")
            print("  Growth may be changing only from FBA exchange bounds,")
            print("  not from the AI layer.")

    # ---------------------------------------------------------------- #
    print("\n" + "=" * 78)
    print("CHECK 3 — is inference inside the 2 second budget?")
    print("=" * 78 + "\n")

    slow = [(k, v.get("compute_time_ms", 0)) for k, v in results.items()
            if v.get("compute_time_ms", 0) > BUDGET_MS]
    worst = max(v.get("compute_time_ms", 0) for v in results.values())
    print(f"  slowest response: {worst:.0f}ms   budget: {BUDGET_MS}ms")
    if slow:
        print(f"  FAIL — over budget: {slow}")
        print("  Note the first call includes model loading; re-run to see")
        print("  the warm number.")
    else:
        print("  PASS")

    # ---------------------------------------------------------------- #
    print("\n" + "=" * 78)
    print("CHECK 4 — where did the predictions come from?")
    print("=" * 78 + "\n")

    for name, data in results.items():
        preds = data.get("expression_predictions") or []
        sources: dict[str, int] = {}
        for p in preds:
            s = p.get("prediction_source", "unknown")
            sources[s] = sources.get(s, 0) + 1
        pathways = len(data.get("active_pathways") or [])
        print(f"  {name:15} sources={sources or 'n/a'}  pathways={pathways}")

    print("\n" + "=" * 78)


if __name__ == "__main__":
    main()