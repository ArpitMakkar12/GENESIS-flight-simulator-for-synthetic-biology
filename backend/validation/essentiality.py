"""Check 1a — Essential genes: does knocking out a gene kill the cell?

For every gene in the model, delete it and re-solve. If growth collapses,
the model calls that gene essential. Then compare with the lab: PRECISE-1K
marks the ~300 genes E. coli K-12 cannot live without.

    docker compose exec backend python -m validation.essentiality

WHY A RICH MEDIUM, NOT THE APP'S GLUCOSE MEDIUM
-----------------------------------------------
The lab essentiality data was measured in rich broth (LB). In rich broth a
cell can import amino acids and nucleotides, so a gene that *makes* one of
them is not essential — thrA, hisG, trpE and ~100 others are marked
non-essential in the data for exactly that reason.

The app's reference medium is glucose minimal salts, where those same genes
ARE essential (the cell has to make everything itself). Screening there and
comparing with LB data would count every biosynthesis gene as a false
positive: a medium mismatch, not a model error.

So this check starts from the app's own aerobic glucose medium and adds the
nutrients LB supplies (RICH_SUPPLEMENTS below). That is the standard way to
approximate LB in flux balance analysis. It is still an approximation — LB
is a digest of yeast and milk protein with no fixed recipe — and the report
says so.

WHAT THIS TESTS, AND WHAT IT DOES NOT
-------------------------------------
This tests the metabolic network itself: its reactions and the gene rules
that say which genes each reaction needs. It does not use the app's
expression-prediction layer, which has no notion of a deleted gene. The
growth-rate check (validation.growth_rates) is the one that exercises the
full engine.
"""

from __future__ import annotations

import argparse
import math
import time
from urllib.parse import unquote

import pandas as pd
from cobra.flux_analysis import single_gene_deletion

from validation.engine import app_medium, apply_bounds, load_model
from validation.sources import CITATION, fetch, results_dir

# ── Rich-medium approximation of LB ─────────────────────────────────────────
# Exchange reactions opened for uptake on top of the app's glucose medium.
# Tryptone supplies amino acids; yeast extract supplies nucleosides,
# nucleobases and vitamins. IDs are BiGG IDs as used by iML1515.
AMINO_ACIDS = [
    "EX_ala__L_e", "EX_arg__L_e", "EX_asn__L_e", "EX_asp__L_e", "EX_cys__L_e",
    "EX_gln__L_e", "EX_glu__L_e", "EX_gly_e", "EX_his__L_e", "EX_ile__L_e",
    "EX_leu__L_e", "EX_lys__L_e", "EX_met__L_e", "EX_phe__L_e", "EX_pro__L_e",
    "EX_ser__L_e", "EX_thr__L_e", "EX_trp__L_e", "EX_tyr__L_e", "EX_val__L_e",
]
NUCLEOSIDES_AND_BASES = [
    "EX_adn_e", "EX_gsn_e", "EX_cytd_e", "EX_uri_e", "EX_thymd_e",   # nucleosides
    "EX_ade_e", "EX_gua_e", "EX_csn_e", "EX_ura_e", "EX_thym_e",     # nucleobases
]
VITAMINS = [
    "EX_thm_e",      # thiamine (B1)
    "EX_ribflv_e",   # riboflavin (B2)
    "EX_nac_e",      # nicotinate (B3)
    "EX_pnto__R_e",  # pantothenate (B5)
    "EX_pydxn_e",    # pyridoxine (B6)
    "EX_btn_e",      # biotin (B7)
    "EX_cbl1_e",     # cobalamin (B12)
    # Folate (B9) is deliberately absent: E. coli has no folate transporter,
    # so opening its uptake would rescue folate-pathway knockouts for a
    # biologically wrong reason.
]
RICH_SUPPLEMENTS = AMINO_ACIDS + NUCLEOSIDES_AND_BASES + VITAMINS

# Uptake allowed for each supplement, mmol/gDW/h. 1.0 puts wild-type growth
# near 2 per hour, the right range for E. coli in LB. Essentiality is a yes/no
# question, so the scores should not depend on it — and the report proves
# that by re-running the screen at each of UPTAKE_CHECKS.
SUPPLEMENT_UPTAKE = 1.0
UPTAKE_CHECKS = [1.0, 2.0, 5.0]

# A knockout counts as lethal below this fraction of wild-type growth.
DEFAULT_THRESHOLD = 0.01
# Re-scored at these too, to show the result does not hinge on one cut-off.
SENSITIVITY_THRESHOLDS = [0.01, 0.05, 0.10, 0.25]


def rich_medium(uptake: float = SUPPLEMENT_UPTAKE) -> dict[str, tuple[float, float]]:
    """The app's aerobic glucose medium plus the LB supplements."""
    medium = dict(app_medium("glucose", "aerobic"))
    for rxn_id in RICH_SUPPLEMENTS:
        medium[rxn_id] = (-uptake, 1000.0)
    return medium


def screen(model, uptake: float, processes: int | None) -> tuple[float, pd.DataFrame, list[str]]:
    """Knock out every gene on the rich medium. Returns (wild-type growth, per-gene table, skipped IDs).

    Runs inside `with model:` so the medium is undone afterwards and the next
    screen starts from the untouched model.
    """
    with model:
        missing = apply_bounds(model, rich_medium(uptake))
        wild_type = model.slim_optimize(error_value=0.0)
        if wild_type <= 1e-6:
            raise SystemExit("The model does not grow on the rich medium, so knockouts cannot be scored.")
        ko = single_gene_deletion(model, processes=processes)

    # COBRApy returns one row per deletion with the gene ID(s) as a set
    ko["locus_tag"] = ko["ids"].map(lambda s: next(iter(s)))
    ko = ko.set_index("locus_tag")
    # An infeasible knockout means no growth at all
    ko["growth"] = ko["growth"].where(ko["status"] == "optimal", 0.0).fillna(0.0).clip(lower=0.0)
    ko["growth_ratio"] = ko["growth"] / wild_type
    return wild_type, ko, missing


def score(predicted: pd.Series, measured: pd.Series) -> dict:
    """Confusion matrix and summary statistics. True = essential."""
    tp = int((predicted & measured).sum())
    fp = int((predicted & ~measured).sum())
    fn = int((~predicted & measured).sum())
    tn = int((~predicted & ~measured).sum())

    def ratio(a: float, b: float) -> float:
        return a / b if b else float("nan")

    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision,
        "recall": recall,
        "specificity": ratio(tn, tn + fp),
        "f1": ratio(2 * precision * recall, precision + recall),
        # Matthews correlation: one number that stays honest when one class
        # is much smaller than the other (here ~8% of genes are essential)
        "mcc": ratio(tp * tn - fp * fn, denom),
        "accuracy": ratio(tp + tn, tp + fp + fn + tn),
    }


def fmt(x: float, digits: int = 3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{digits}f}"


def gene_list(df: pd.DataFrame) -> str:
    """Markdown table of genes for the report."""
    if df.empty:
        return "_None._\n"
    rows = ["| Gene | Locus | Product | Knockout growth (% of wild type) |", "| --- | --- | --- | --- |"]
    for locus, r in df.sort_values("gene_name").iterrows():
        rows.append(f"| {r.gene_name} | {locus} | {r.gene_product} | {r.growth_ratio * 100:.1f}% |")
    return "\n".join(rows) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help="lethal below this fraction of wild-type growth (default 0.01)")
    ap.add_argument("--model", default=None,
                    help="SBML file to use instead of the app's iML1515 (development only)")
    ap.add_argument("--processes", type=int, default=None,
                    help="worker processes for the knockout screen (default: COBRApy decides)")
    args = ap.parse_args()
    started = time.time()

    print("Essential gene check")
    model = load_model(args.model)
    truth = pd.read_csv(fetch("gene_info.csv"), index_col="locus_tag")
    truth["essential"] = truth["essential"].astype(str).str.lower().eq("true")

    # ── The screen: every gene, one at a time, on the chosen medium ──
    print(f"  Knocking out {len(model.genes)} genes one at a time...", flush=True)
    wild_type, ko, missing = screen(model, SUPPLEMENT_UPTAKE, args.processes)
    print(f"  Wild-type growth on rich medium: {wild_type:.3f} h⁻¹")
    if missing:
        print(f"  Not in this model, skipped: {', '.join(missing)}")

    # ── Robustness: the same screen at other supplement uptake rates ──
    uptake_rows = []
    for up in UPTAKE_CHECKS:
        wt_u, ko_u, _ = (wild_type, ko, missing) if up == SUPPLEMENT_UPTAKE else screen(model, up, args.processes)
        idx = ko_u.index.intersection(truth.index)
        s = score(ko_u.loc[idx, "growth_ratio"] < args.threshold, truth.loc[idx, "essential"])
        uptake_rows.append((up, wt_u, s))

    in_both = ko.index.intersection(truth.index)
    not_in_truth = ko.index.difference(truth.index)
    df = ko.loc[in_both, ["growth", "growth_ratio"]].join(
        truth.loc[in_both, ["gene_name", "gene_product", "essential"]])
    df["gene_name"] = df["gene_name"].fillna(df.index.to_series())
    # The source file URL-encodes commas in product names ("5%2C10-methylene...")
    df["gene_product"] = df["gene_product"].fillna("").map(unquote)
    df["predicted_essential"] = df["growth_ratio"] < args.threshold
    df["outcome"] = df.apply(
        lambda r: ("TP" if r.essential else "FP") if r.predicted_essential else ("FN" if r.essential else "TN"),
        axis=1,
    )

    m = score(df["predicted_essential"], df["essential"])
    lab_essential_total = int(truth["essential"].sum())
    lab_essential_in_model = int(df["essential"].sum())

    sensitivity = []
    for t in SENSITIVITY_THRESHOLDS:
        s = score(df["growth_ratio"] < t, df["essential"])
        sensitivity.append((t, s))

    # ── Write results ──
    out = results_dir()
    df.sort_values(["outcome", "gene_name"]).to_csv(out / "essentiality_genes.csv", index_label="locus_tag")

    fn = df[df.outcome == "FN"]
    fp = df[df.outcome == "FP"]
    elapsed = time.time() - started

    sens_rows = "\n".join(
        f"| {t * 100:g}% | {s['tp']} | {s['fp']} | {s['fn']} | {fmt(s['precision'])} | {fmt(s['recall'])} | {fmt(s['f1'])} | {fmt(s['mcc'])} |"
        for t, s in sensitivity
    )
    uptake_table = "\n".join(
        f"| {up:g}{' (used)' if up == SUPPLEMENT_UPTAKE else ''} | {wt_u:.2f} | {s['tp']} | {s['fp']} | {s['fn']} | {fmt(s['f1'])} | {fmt(s['mcc'])} |"
        for up, wt_u, s in uptake_rows
    )

    report = f"""# Essential gene check

**Model:** {model.id} ({len(model.genes)} genes) · **Medium:** rich-broth approximation (the app's aerobic glucose medium plus {len(RICH_SUPPLEMENTS) - len(missing)} nutrients LB supplies: amino acids, nucleosides and vitamins) · **Lethal below:** {args.threshold * 100:g}% of wild-type growth · **Wild-type growth:** {wild_type:.3f} h⁻¹

**Ground truth:** {CITATION}, `essential` column (measured in rich medium).

## Result

Of the {len(df):,} genes in both the model and the lab data, the model calls **{int(df.predicted_essential.sum())}** essential; the lab says **{lab_essential_in_model}**.

| Measure | Value | What it means |
| --- | --- | --- |
| Precision | {fmt(m['precision'])} | Of the genes the model calls essential, the share the lab agrees are essential |
| Recall | {fmt(m['recall'])} | Of the lab's essential genes, the share the model catches |
| F1 | {fmt(m['f1'])} | Balance of precision and recall |
| MCC | {fmt(m['mcc'])} | Matthews correlation, −1 to 1; 0 is no better than chance. The fairest single number here, because essential genes are a small minority |
| Accuracy | {fmt(m['accuracy'])} | Shown for completeness only — calling every gene non-essential would already score about {fmt(1 - lab_essential_in_model / len(df), 2)} |

| | Lab: essential | Lab: not essential |
| --- | --- | --- |
| **Model: essential** | {m['tp']} (true positive) | {m['fp']} (false positive) |
| **Model: not essential** | {m['fn']} (false negative) | {m['tn']} (true negative) |

## Coverage — what this model can speak to

The lab lists **{lab_essential_total}** essential genes; **{lab_essential_in_model}** of them are in the model. Most of the rest work outside metabolism (DNA replication, transcription, translation, cell division), which a metabolic model does not represent — so it cannot predict them either way. {len(not_in_truth)} model gene(s) have no lab record and are left out of the scoring.

## Do the setup choices matter?

Two choices could have steered the result: the lethality cut-off, and how much of each LB nutrient the cell may take up. The screen is re-scored and re-run with other values; if the scores held only for one value, that value would be suspect.

**Lethality cut-off** (same screen, re-scored):

| Lethal below | TP | FP | FN | Precision | Recall | F1 | MCC |
| --- | --- | --- | --- | --- | --- | --- | --- |
{sens_rows}

**Nutrient uptake** (screen re-run; mmol/gDW/h per nutrient):

| Uptake | Wild-type growth (h⁻¹) | TP | FP | FN | F1 | MCC |
| --- | --- | --- | --- | --- | --- | --- |
{uptake_table}

## Where the model disagrees with the lab

**False negatives — the lab says essential, the model says the cell survives ({len(fn)}).** Usually the model has an alternative route the real cell cannot use (the enzyme is absent, too slow or regulated off), or the gene matters for something besides its metabolic reaction.

{gene_list(fn)}
**False positives — the model says lethal, the lab says the cell survives ({len(fp)}).** Usually the real cell has a backup the model lacks (an unannotated isozyme or salvage pathway), or LB provides a nutrient this medium approximation leaves out.

{gene_list(fp)}
---
Generated by `python -m validation.essentiality` in {elapsed:.0f} s. Per-gene results: `essentiality_genes.csv`.
"""
    (out / "essentiality_summary.md").write_text(report, encoding="utf-8")

    print(f"  Scored {len(df)} genes in {elapsed:.0f} s")
    print(f"  Precision {fmt(m['precision'])} · Recall {fmt(m['recall'])} · F1 {fmt(m['f1'])} · MCC {fmt(m['mcc'])}")
    print(f"  TP {m['tp']} · FP {m['fp']} · FN {m['fn']} · TN {m['tn']}")
    print(f"  Wrote {out / 'essentiality_summary.md'}")


if __name__ == "__main__":
    main()