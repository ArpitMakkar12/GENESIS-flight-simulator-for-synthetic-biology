"""Check 1b — Growth rates: how fast does GENESIS say wild-type E. coli grows?

Takes every experiment in PRECISE-1K that measured the growth rate of
wild-type E. coli under a condition GENESIS can simulate, runs GENESIS on
the same condition, and compares the two.

    docker compose exec backend python -m validation.growth_rates

Two predictions per condition, so the report can show what each layer adds:

    iML1515 only  — the metabolic model on the app's medium, nothing else.
                    Classic flux balance analysis; it has no idea of
                    temperature or pH.
    GENESIS       — the full engine, exactly as the Simulate page runs it:
                    regulators → expression → reaction limits → FBA.

WHICH EXPERIMENTS COUNT
-----------------------
A sample is used only if GENESIS can represent it honestly (see
KEEP_IF below): unmodified MG1655 (the strain iML1515 describes), not
evolved, in M9 minimal salts with ammonium and air, one carbon source GENESIS
supports, and no supplements or antibiotics. Replicates of the same
condition are averaged. Every rule is printed in the report with how many
samples it removed, so nothing is dropped silently.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import re
import time
from html import escape

import pandas as pd

from validation.engine import app_medium, apply_bounds, load_model
from validation.sources import CITATION, fetch, results_dir

GROWTH = "Growth Rate (1/hr)"

# PRECISE-1K carbon source name -> GENESIS carbon_source value.
# D-arabinose is a different sugar from the L-arabinose GENESIS models, so it is not here.
CARBON_MAP = {
    "glucose": "glucose", "glycerol": "glycerol", "acetate": "acetate",
    "fructose": "fructose", "xylose": "xylose", "galactose": "galactose",
    "lactose": "lactose", "succinate": "succinate", "L-arabinose": "arabinose",
}
WILD_TYPE = "Escherichia coli K-12 MG1655"


def single_carbon(value) -> str | None:
    """'glucose(4)' -> 'glucose'; None for mixtures or blanks."""
    if not isinstance(value, str) or "+" in value or "," in value:
        return None
    return re.sub(r"\(.*?\)", "", value).strip() or None


# Each rule: (what it means in plain words, test on the metadata table)
KEEP_IF = [
    ("growth rate was measured", lambda m: m[GROWTH].fillna(0) > 0),
    ("strain is MG1655", lambda m: m["Strain"] == "MG1655"),
    ("no gene deletions or other changes", lambda m: m["Strain Description"].fillna("").str.strip() == WILD_TYPE),
    ("not an evolved strain", lambda m: m["Evolved Sample"] == "No"),
    ("M9 minimal medium", lambda m: m["Base Media"] == "M9"),
    ("ammonium as nitrogen source", lambda m: m["Nitrogen Source (g/L)"] == "NH4Cl(1)"),
    ("oxygen as electron acceptor (aerobic)", lambda m: m["Electron Acceptor"] == "O2"),
    ("no supplements", lambda m: m["Supplement"].isna()),
    ("no antibiotic (no plasmid)", lambda m: m["Antibiotic for selection"].isna()),
    ("one carbon source that GENESIS supports",
     lambda m: m["Carbon Source (g/L)"].map(single_carbon).isin(CARBON_MAP.keys())),
]


def select_conditions(meta: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    """Apply KEEP_IF in order. Returns (one row per condition, funnel of samples left after each rule)."""
    keep = pd.Series(True, index=meta.index)
    funnel = [("all samples in PRECISE-1K", len(meta))]
    for label, rule in KEEP_IF:
        keep &= rule(meta).fillna(False)
        funnel.append((label, int(keep.sum())))

    samples = meta[keep].copy()
    samples["carbon_source"] = samples["Carbon Source (g/L)"].map(single_carbon).map(CARBON_MAP)
    samples["temperature"] = samples["Temperature (C)"].astype(float)
    samples["ph"] = samples["pH"].astype(float)

    # PRECISE-1K stores one row per sequencing library, and copies the
    # experiment's single growth rate onto each replicate library. Counting
    # those copies as separate measurements would overstate n and shrink the
    # spread, so collapse to one value per experiment (study + condition) first.
    experiments = samples.groupby(["study", "condition", "carbon_source", "temperature", "ph"]).agg(
        growth=(GROWTH, "mean"),
        libraries=(GROWTH, "size"),
        doi=("DOI", "first"),
    ).reset_index()

    cond = experiments.groupby(["carbon_source", "temperature", "ph"]).agg(
        n=("growth", "size"),                 # independent experiments
        libraries=("libraries", "sum"),       # sequencing libraries behind them
        measured=("growth", "mean"),
        measured_sd=("growth", "std"),
        studies=("study", lambda s: "; ".join(sorted(set(s)))),
        doi=("doi", lambda s: "; ".join(sorted(set(map(str, s))))),
    ).reset_index()
    cond["measured_sd"] = cond["measured_sd"].fillna(0.0)  # one experiment has no spread
    return cond, funnel


def label(row) -> str:
    return f"{row.carbon_source}, {row.temperature:g} °C" + ("" if row.ph == 7 else f", pH {row.ph:g}")


# ── The two engines ──────────────────────────────────────────────────────────

def predict_base(model, carbon: str) -> float:
    """iML1515 on the app's medium, nothing else."""
    with model:
        apply_bounds(model, app_medium(carbon, "aerobic"))
        return model.slim_optimize(error_value=0.0)


async def predict_genesis(runner, carbon: str, temperature: float, ph: float) -> float:
    """The full engine, the same call the Simulate page makes (minus saving to the database)."""
    result = await runner.run(
        construct_id=None,
        raw_sequence=None,
        temperature=temperature,
        ph=ph,
        oxygen_level="aerobic",
        carbon_source=carbon,
        nitrogen_source="ammonium",
    )
    return float(result["growth_rate"])


# ── Statistics ───────────────────────────────────────────────────────────────

def stats(pred: pd.Series, meas: pd.Series) -> dict:
    ok = pred.notna() & meas.notna()
    # Round first: the LP solver returns "equal" growth rates that differ in
    # the 15th decimal, and ranking those would invent an order between
    # conditions the model actually treats as identical. 4 places matches
    # what the app itself reports.
    p, m = pred[ok].round(4), meas[ok].round(4)
    if len(p) < 2:
        return {"n": int(len(p))}
    err = p - m
    return {
        "n": int(len(p)),
        "mae": float(err.abs().mean()),
        "bias": float(err.mean()),                    # >0 means it over-predicts on average
        "median_ratio": float((p / m).median()),       # 1.0 = right size
        "pearson": float(p.corr(m, method="pearson")),
        # Spearman = Pearson on ranks: does it put the conditions in the right
        # order? Computed directly because pandas' own version needs scipy.
        "spearman": float(p.rank().corr(m.rank(), method="pearson")),
    }


def fmt(x, digits=3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{digits}f}"


# ── The chart: one row per condition, measured vs each prediction ────────────
# Colours are the validated categorical pair (blue, orange); the measured
# value is the reference, so it is drawn in ink, not as a series. Shapes
# differ too, so the chart never relies on colour alone.

INK, INK_SOFT, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SERIES = {"base": ("#2a78d6", "iML1515 only", "circle"), "genesis": ("#eb6834", "GENESIS (full engine)", "square")}


def _marker(shape: str, x: float, y: float, color: str, tip: str) -> str:
    t = f"<title>{escape(tip)}</title>"
    # 2px surface ring keeps overlapping markers distinct
    if shape == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{color}" stroke="{SURFACE}" stroke-width="2">{t}</circle>'
    if shape == "square":
        return f'<rect x="{x - 5:.1f}" y="{y - 5:.1f}" width="10" height="10" rx="1.5" fill="{color}" stroke="{SURFACE}" stroke-width="2">{t}</rect>'
    # diamond = measured
    return (f'<path d="M{x:.1f} {y - 6.5:.1f} L{x + 6.5:.1f} {y:.1f} L{x:.1f} {y + 6.5:.1f} L{x - 6.5:.1f} {y:.1f} Z" '
            f'fill="{SURFACE}" stroke="{INK}" stroke-width="2">{t}</path>')


def chart_svg(df: pd.DataFrame, engines: list[str]) -> str:
    rows = df.sort_values("measured", ascending=False).reset_index(drop=True)
    left, right, top, row_h = 150, 40, 64, 40
    width = 720
    plot_w = width - left - right
    height = top + row_h * len(rows) + 46

    vals = [rows.measured + rows.measured_sd] + [rows[e] for e in engines if e in rows]
    x_max = max(float(pd.concat(vals).max()), 0.1)
    step = 0.2 if x_max <= 1.2 else 0.5
    x_max = math.ceil(x_max / step) * step

    def X(v: float) -> float:
        return left + plot_w * v / x_max

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           f'font-family="system-ui, -apple-system, Segoe UI, sans-serif" role="img" '
           f'aria-label="Measured and predicted growth rate for each condition">',
           f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>']

    # legend (always present: 2+ series)
    lx = left
    items = [("measured", "Measured (± SD)", "diamond", INK)] + [(e, SERIES[e][1], SERIES[e][2], SERIES[e][0]) for e in engines]
    for _key, name, shape, color in items:
        out.append(_marker(shape, lx + 6, 24, color, name))
        out.append(f'<text x="{lx + 18}" y="28" font-size="12" fill="{INK_SOFT}">{escape(name)}</text>')
        lx += 30 + 7 * len(name)

    # grid + x axis
    base_y = top + row_h * len(rows)
    v = 0.0
    while v <= x_max + 1e-9:
        out.append(f'<line x1="{X(v):.1f}" y1="{top - 8}" x2="{X(v):.1f}" y2="{base_y}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{X(v):.1f}" y="{base_y + 16}" font-size="11" fill="{INK_SOFT}" text-anchor="middle">{"0" if v < 1e-9 else f"{v:.1f}"}</text>')
        v += step
    out.append(f'<text x="{left + plot_w / 2:.1f}" y="{base_y + 36}" font-size="12" fill="{INK_SOFT}" text-anchor="middle">Growth rate (per hour)</text>')

    for i, r in rows.iterrows():
        y = top + row_h * i + row_h / 2
        out.append(f'<text x="{left - 12}" y="{y + 4:.1f}" font-size="12" fill="{INK}" text-anchor="end">{escape(label(r))}</text>')
        # light connector from measured to each prediction: the error, drawn
        for e in engines:
            if e in rows and pd.notna(r[e]):
                out.append(f'<line x1="{X(r.measured):.1f}" y1="{y:.1f}" x2="{X(r[e]):.1f}" y2="{y:.1f}" stroke="{SERIES[e][0]}" stroke-opacity="0.35" stroke-width="2"/>')
        if r.measured_sd > 0:
            out.append(f'<line x1="{X(r.measured - r.measured_sd):.1f}" y1="{y:.1f}" x2="{X(r.measured + r.measured_sd):.1f}" y2="{y:.1f}" stroke="{INK}" stroke-width="1.5"/>')
            for xv in (r.measured - r.measured_sd, r.measured + r.measured_sd):
                out.append(f'<line x1="{X(xv):.1f}" y1="{y - 4:.1f}" x2="{X(xv):.1f}" y2="{y + 4:.1f}" stroke="{INK}" stroke-width="1.5"/>')
        for e in engines:
            if e in rows and pd.notna(r[e]):
                color, name, shape = SERIES[e]
                out.append(_marker(shape, X(r[e]), y, color, f"{label(r)} — {name}: {r[e]:.3f} per hour"))
        sd = f" ± {r.measured_sd:.3f}" if r.measured_sd > 0 else ""
        out.append(_marker("diamond", X(r.measured), y, INK, f"{label(r)} — measured: {r.measured:.3f}{sd} per hour ({r.n} experiment{'s' if r.n != 1 else ''})"))

    out.append("</svg>")
    return "\n".join(out)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--engine", choices=["both", "base", "genesis"], default="both",
                    help="which predictions to make (default: both)")
    ap.add_argument("--model", default=None,
                    help="SBML file for the iML1515-only prediction instead of the app's model (development only; "
                         "implies --engine base)")
    args = ap.parse_args()
    if args.model:
        args.engine = "base"
    engines = ["base", "genesis"] if args.engine == "both" else [args.engine]
    started = time.time()

    print("Growth rate check")
    meta = pd.read_csv(fetch("metadata.csv"), index_col=0)
    cond, funnel = select_conditions(meta)
    print(f"  {funnel[1][1]} samples with a measured growth rate → {funnel[-1][1]} usable → {len(cond)} distinct conditions")
    if cond.empty:
        raise SystemExit("No usable conditions — check the filter rules in KEEP_IF.")

    errors: list[str] = []
    if "base" in engines:
        model = load_model(args.model)
        cond["base"] = [predict_base(model, c) for c in cond.carbon_source]

    if "genesis" in engines:
        from app.services.simulation_runner import SimulationRunner
        runner = SimulationRunner()
        preds = []
        for r in cond.itertuples():
            try:
                preds.append(asyncio.run(predict_genesis(runner, r.carbon_source, r.temperature, r.ph)))
            except Exception as exc:  # report it, keep going with the other conditions
                errors.append(f"{label(r)}: {type(exc).__name__}: {exc}")
                preds.append(float("nan"))
            print(f"    {label(r):28} measured {r.measured:.3f}  GENESIS {preds[-1]:.3f}", flush=True)
        cond["genesis"] = preds

    summary = {e: stats(cond[e], cond["measured"]) for e in engines}

    # ── Write results ──
    out = results_dir()
    cond.sort_values("measured", ascending=False).to_csv(out / "growth_rates.csv", index=False, float_format="%.4f")
    (out / "growth_rates.svg").write_text(chart_svg(cond, engines), encoding="utf-8")

    funnel_rows = "\n".join(f"| {lbl} | {n:,} |" for lbl, n in funnel)
    names = {"base": "iML1515 only", "genesis": "GENESIS (full engine)"}
    stat_rows = "\n".join(
        f"| {names[e]} | {s.get('n', 0)} | {fmt(s.get('mae'))} | {fmt(s.get('bias'), 3)} | {fmt(s.get('median_ratio'), 2)} | {fmt(s.get('spearman'), 2)} | {fmt(s.get('pearson'), 2)} |"
        for e, s in summary.items()
    )
    cond_rows = "\n".join(
        "| " + " | ".join(
            [label(r), str(r.n), f"{r.measured:.3f}" + (f" ± {r.measured_sd:.3f}" if r.measured_sd > 0 else "")]
            + [fmt(getattr(r, e)) for e in engines]
            + [r.doi.replace("; ", "<br>")]
        ) + " |"
        for r in cond.sort_values("measured", ascending=False).itertuples()
    )
    head_engines = " | ".join(names[e] for e in engines)
    sep_engines = " | ".join("---" for _ in engines)
    small_n = len(cond) < 10
    err_block = ("\n## Conditions that failed to run\n\n" + "\n".join(f"- {e}" for e in errors) + "\n") if errors else ""

    report = f"""# Growth rate check

**Ground truth:** {CITATION}, column `{GROWTH}` with each experiment's culture conditions.
**Predictions:** {", ".join(names[e] for e in engines)}.

![Measured and predicted growth rate per condition](growth_rates.svg)

## Result

| Engine | Conditions | Mean absolute error (h⁻¹) | Bias (h⁻¹) | Median predicted ÷ measured | Rank agreement (Spearman) | Linear agreement (Pearson) |
| --- | --- | --- | --- | --- | --- | --- |
{stat_rows}

How to read these: **mean absolute error** is the typical miss in growth-rate units. **Bias** above zero means the engine predicts faster growth than measured on average — expected for flux balance analysis, which assumes the cell grows as fast as its network allows. **Median ratio** is the same idea as a multiple. **Spearman** asks whether the engine puts the conditions in the right order (1 = perfect order), which matters most when only a handful of conditions are available. **Pearson** asks whether the values fall on a straight line.
{"" if not small_n else f'''
**Caution — {len(cond)} conditions is a small sample.** With this few points a correlation can swing a long way on one condition, so read the rank agreement and each row below rather than leaning on one coefficient. More conditions need more experiments that GENESIS can represent (see the funnel).
'''}
## Per condition

| Condition | Experiments | Measured (h⁻¹) | {head_engines} | Source |
| --- | --- | --- | {sep_engines} | --- |
{cond_rows}

## Which experiments were used

Each rule is applied in order; the number is how many samples were left after it.

| Rule | Samples left |
| --- | --- |
{funnel_rows}

PRECISE-1K stores one row per sequencing library and repeats each experiment's growth rate on every replicate library, so libraries are first collapsed to one value per experiment. Experiments with the same carbon source, temperature and pH are then averaged into one condition; **Experiments** counts the independent measurements behind each, and ± is their standard deviation.

**Not covered:**
- **Oxygen.** PRECISE-1K reports no growth rates for anaerobic cultures, so this check says nothing about growth without oxygen.
- **pH.** Every usable experiment is at pH {", ".join(f"{v:g}" for v in sorted(cond.ph.unique()))}. The only wild-type experiments at other pH values carry an antibiotic (a plasmid) and are excluded, so GENESIS's pH response is untested here.
- **Temperature.** Only {" and ".join(f"{v:g} °C" for v in sorted(cond.temperature.unique()))} {"is" if cond.temperature.nunique() == 1 else "are"} covered.
{err_block}
---
Generated by `python -m validation.growth_rates` in {time.time() - started:.0f} s. Data: `growth_rates.csv`.
"""
    (out / "growth_rates_summary.md").write_text(report, encoding="utf-8")

    for e, s in summary.items():
        print(f"  {names[e]:22} MAE {fmt(s.get('mae'))} · bias {fmt(s.get('bias'))} · Spearman {fmt(s.get('spearman'), 2)} · Pearson {fmt(s.get('pearson'), 2)}")
    if errors:
        print(f"  {len(errors)} condition(s) failed to run — listed in the report")
    print(f"  Wrote {out / 'growth_rates_summary.md'}")


if __name__ == "__main__":
    main()