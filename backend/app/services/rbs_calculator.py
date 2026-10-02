"""RBS calculator — how strongly will a ribosome start translating here?

Owned by: Keshav

WHAT THIS IS
------------
A promoter decides how many mRNA copies a gene gets. The ribosome
binding site decides how much PROTEIN comes off each copy. Both matter:

    [promoter] ... [RBS] [ATG] [coding sequence]
         |            |
      how much     how much
        mRNA        protein

This module scores the RBS — the stretch just before the start codon
that a ribosome latches onto.

THE PHYSICS
-----------
The ribosome's own 16S rRNA ends in a sequence that base-pairs with the
RBS. Tighter pairing means a firmer grip. Free energy measures that
tightness, in kcal/mol, and more negative means stronger.

Five terms contribute (Salis, Mirsky & Voigt 2009):

    dG_mRNA_rRNA   pairing between the Shine-Dalgarno motif and the
                   16S rRNA 3' tail. The dominant term.
    dG_start       start codon identity. ATG binds best, then GTG, TTG.
    dG_spacing     distance from the SD motif to the start codon.
                   About 5 bases is optimal; closer or further both hurt.
    dG_standby     the landing pad just upstream of the SD.
    dG_mRNA        cost of unfolding mRNA secondary structure. If the
                   message is knotted up, the ribosome cannot reach in.

    dG_total = dG_mRNA_rRNA + dG_start + dG_spacing - dG_standby - dG_mRNA

    translation rate  proportional to  exp(-beta * dG_total)

The relationship is exponential, which is why two RBS sequences
differing by a few bases can differ a hundredfold in protein output.

ACCURACY AND HONESTY
--------------------
Two terms need real RNA folding, which requires ViennaRNA:

    dG_mRNA     folding of the mRNA around the start codon
    dG_standby  folding of the standby site

If ViennaRNA is installed, this module uses it and reports
method="vienna". If not, it falls back to a nearest-neighbour base
pairing approximation and reports method="approximate".

The fallback gets the DIRECTION right — strong RBSs score higher than
weak ones — but the absolute numbers are not comparable to the
published RBS Calculator. Every result carries its method, so an
approximate number is never mistaken for a full calculation.

    pip install ViennaRNA
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------- #

# The 3' tail of E. coli 16S ribosomal RNA, written 5'->3' in DNA
# alphabet. The Shine-Dalgarno motif in an mRNA pairs with this.
# Canonical SD is AGGAGG, which pairs with CCTCCT here.
ANTI_SD = "ACCTCCTTA"

# Boltzmann-like scaling from the RBS Calculator, in mol/kcal.
BETA = 0.45

# Arbitrary scaling so typical translation rates land in a readable
# range, as the published calculator also does. Only ratios are
# meaningful, never the absolute value.
RATE_SCALE = 2500.0

# Free energy of the start codon itself, kcal/mol (Salis 2009).
START_CODON_DG = {
    "ATG": -1.194,
    "GTG": -0.0748,
    "TTG": -0.0435,
    "CTG": -0.03,
    "ATT": 0.0,
    "ATC": 0.0,
}

# Optimal gap between the end of the SD motif and the start codon.
OPTIMAL_SPACING = 5

# How far upstream of the start codon to look for an SD motif.
SD_SEARCH_WINDOW = 20

# Window used for folding calculations around the start codon.
FOLD_UPSTREAM = 35
FOLD_DOWNSTREAM = 35

# Per-base-pair energies for the approximate mode, kcal/mol. Real
# nearest-neighbour models use stacking energies between adjacent
# pairs; this uses single pairs, which is cruder but directionally
# correct and transparent about it.
PAIR_ENERGY = {
    ("G", "C"): -3.0, ("C", "G"): -3.0,
    ("A", "T"): -2.0, ("T", "A"): -2.0,
    ("G", "T"): -1.0, ("T", "G"): -1.0,   # wobble pair, G-U in RNA
}

_VIENNA = None


def _vienna():
    """Load ViennaRNA once, if it is installed."""
    global _VIENNA
    if _VIENNA is None:
        try:
            import RNA  # type: ignore

            _VIENNA = RNA
        except ImportError:
            _VIENNA = False
    return _VIENNA or None


@dataclass
class RBSResult:
    """Everything that went into one RBS score."""
    translation_rate: float          # arbitrary units, compare by ratio
    dg_total: float                  # kcal/mol, more negative is stronger
    dg_mrna_rrna: float
    dg_start: float
    dg_spacing: float
    dg_standby: float
    dg_mrna: float
    sd_sequence: str                 # the motif we found
    sd_position: int                 # bases upstream of the start codon
    spacing: int
    start_codon: str
    method: str                      # "vienna" or "approximate"
    warnings: list[str] = field(default_factory=list)

    @property
    def strength(self) -> str:
        """Rough band, for reading at a glance."""
        if self.translation_rate >= 10_000:
            return "very strong"
        if self.translation_rate >= 1_000:
            return "strong"
        if self.translation_rate >= 100:
            return "moderate"
        if self.translation_rate >= 10:
            return "weak"
        return "very weak"

    def describe(self) -> str:
        return (f"TIR={self.translation_rate:,.0f} ({self.strength})  "
                f"dG={self.dg_total:+.2f} kcal/mol  "
                f"SD={self.sd_sequence or 'none'} at -{self.sd_position}  "
                f"spacing={self.spacing}  [{self.method}]")


# --------------------------------------------------------------------- #
# Energy terms
# --------------------------------------------------------------------- #

def _pair_energy(a: str, b: str) -> float:
    """Energy of one base pair. Zero if the bases do not pair."""
    return PAIR_ENERGY.get((a, b), 0.0)


def _duplex_energy_approx(sd: str) -> float:
    """Best binding energy between an SD candidate and the 16S tail.

    Slides the SD along the anti-SD and keeps the strongest alignment.
    The anti-SD is reversed because the two strands run antiparallel.
    """
    if not sd:
        return 0.0

    target = ANTI_SD[::-1]
    best = 0.0

    for offset in range(-len(sd) + 1, len(target)):
        energy = 0.0
        for i, base in enumerate(sd):
            j = offset + i
            if 0 <= j < len(target):
                energy += _pair_energy(base, target[j])
        best = min(best, energy)

    return best


def _duplex_energy_vienna(sd: str) -> float | None:
    """Duplex energy from ViennaRNA, if available."""
    rna = _vienna()
    if rna is None or not sd:
        return None
    try:
        duplex = rna.duplexfold(sd.replace("T", "U"),
                                ANTI_SD.replace("T", "U"))
        return float(duplex.energy)
    except Exception:
        return None


def _fold_energy(sequence: str) -> tuple[float, str]:
    """Folding free energy of a stretch of mRNA.

    Returns (energy, method). A strongly folded message hides the RBS,
    so this works against translation.
    """
    if not sequence:
        return 0.0, "none"

    rna = _vienna()
    if rna is not None:
        try:
            _, mfe = rna.fold(sequence.replace("T", "U"))
            return float(mfe), "vienna"
        except Exception:
            pass

    # Approximation: GC-rich sequence folds more tightly. Real folding
    # depends on which bases can reach each other, not just how many
    # there are, so this is a rough stand-in.
    gc = sum(1 for b in sequence if b in "GC") / max(len(sequence), 1)
    return -0.12 * len(sequence) * gc, "approximate"


def _spacing_penalty(spacing: int) -> float:
    """Energy cost of non-optimal SD to start-codon distance.

    Too far and the ribosome cannot bridge the gap; too close and it
    cannot fit. Both are penalised, the near side more steeply.
    """
    d = spacing - OPTIMAL_SPACING
    if d > 0:
        return 0.048 * d * d + 0.24 * d
    if d < 0:
        return 0.5 * d * d
    return 0.0


def _find_sd(upstream: str) -> tuple[str, int, float, str]:
    """Locate the strongest Shine-Dalgarno candidate upstream.

    Tries every window in the search region and keeps whichever binds
    the 16S tail most tightly. Returns (motif, distance from start
    codon, binding energy, method).
    """
    window = upstream[-SD_SEARCH_WINDOW:] if upstream else ""
    if not window:
        return "", 0, 0.0, "none"

    best = ("", 0, 0.0, "approximate")

    for length in (6, 5, 7, 4, 8):
        for start in range(len(window) - length + 1):
            candidate = window[start:start + length]
            if not re.fullmatch(r"[ACGT]+", candidate):
                continue

            energy = _duplex_energy_vienna(candidate)
            method = "vienna"
            if energy is None:
                energy = _duplex_energy_approx(candidate)
                method = "approximate"

            if energy < best[2]:
                distance = len(window) - (start + length)
                best = (candidate, distance, energy, method)

    return best


# --------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------- #

def calculate_rbs(
    sequence: str,
    start_position: int | None = None,
) -> RBSResult:
    """Score the ribosome binding site in front of a start codon.

    sequence        DNA containing the RBS and the start of the gene
    start_position  index of the start codon's first base. If omitted,
                    the first ATG/GTG/TTG with at least 10 bases in
                    front of it is used.
    """
    seq = (sequence or "").upper().strip().replace("U", "T")
    warnings: list[str] = []

    if not seq:
        return _empty_result(["empty sequence"])

    bad = set(seq) - set("ACGTN")
    if bad:
        warnings.append(f"non-DNA characters: {sorted(bad)[:3]}")

    # ---- locate the start codon ----
    if start_position is None:
        start_position = -1
        for i in range(10, len(seq) - 2):
            if seq[i:i + 3] in START_CODON_DG:
                start_position = i
                break
        if start_position < 0:
            return _empty_result(
                warnings + ["no start codon found with enough upstream context"]
            )

    if start_position < 0 or start_position + 3 > len(seq):
        return _empty_result(warnings + ["start position outside the sequence"])

    start_codon = seq[start_position:start_position + 3]
    if start_codon not in START_CODON_DG:
        warnings.append(f"unusual start codon: {start_codon}")

    upstream = seq[:start_position]
    if len(upstream) < 10:
        warnings.append(
            f"only {len(upstream)}bp upstream — too little to find an SD motif"
        )

    # ---- the five terms ----
    sd_seq, sd_pos, dg_hybrid, sd_method = _find_sd(upstream)
    dg_start = START_CODON_DG.get(start_codon, 0.0)
    spacing = sd_pos
    dg_spacing = _spacing_penalty(spacing)

    fold_region = seq[
        max(0, start_position - FOLD_UPSTREAM):
        start_position + FOLD_DOWNSTREAM
    ]
    dg_mrna, fold_method = _fold_energy(fold_region)

    standby_region = upstream[-(SD_SEARCH_WINDOW + 15):-SD_SEARCH_WINDOW] \
        if len(upstream) > SD_SEARCH_WINDOW + 15 else ""
    dg_standby, _ = _fold_energy(standby_region)

    dg_total = dg_hybrid + dg_start + dg_spacing - dg_standby - dg_mrna

    # Exponential relationship: a few kcal/mol becomes orders of
    # magnitude in protein output.
    rate = RATE_SCALE * math.exp(-BETA * dg_total)
    rate = min(rate, 1e7)      # cap, so a pathological input cannot
                               # produce an absurd flux bound downstream

    method = "vienna" if (_vienna() and fold_method == "vienna") else "approximate"
    if method == "approximate":
        warnings.append(
            "ViennaRNA not installed — folding terms are approximated. "
            "Ratios between sequences are meaningful; absolute values "
            "are not comparable to the published RBS Calculator."
        )

    return RBSResult(
        translation_rate=rate,
        dg_total=dg_total,
        dg_mrna_rrna=dg_hybrid,
        dg_start=dg_start,
        dg_spacing=dg_spacing,
        dg_standby=dg_standby,
        dg_mrna=dg_mrna,
        sd_sequence=sd_seq,
        sd_position=sd_pos,
        spacing=spacing,
        start_codon=start_codon,
        method=method,
        warnings=warnings,
    )


def rbs_score(sequence: str, start_position: int | None = None) -> float:
    """Just the translation initiation rate, for callers that want one number."""
    return calculate_rbs(sequence, start_position).translation_rate


def relative_rbs_score(sequence: str, start_position: int | None = None) -> float:
    """Translation rate on a 0 to 1 scale, for feeding a model.

    Log-compressed because raw rates span several orders of magnitude.
    """
    rate = rbs_score(sequence, start_position)
    return min(1.0, max(0.0, math.log10(max(rate, 1.0)) / 7.0))


def _empty_result(warnings: list[str]) -> RBSResult:
    return RBSResult(
        translation_rate=0.0, dg_total=0.0, dg_mrna_rrna=0.0,
        dg_start=0.0, dg_spacing=0.0, dg_standby=0.0, dg_mrna=0.0,
        sd_sequence="", sd_position=0, spacing=0, start_codon="",
        method="none", warnings=warnings,
    )


# --------------------------------------------------------------------- #
# Smoke test:  python backend/app/services/rbs_calculator.py
# --------------------------------------------------------------------- #

if __name__ == "__main__":
    print("=" * 76)
    print("RBS CALCULATOR")
    print("=" * 76)

    print(f"\nViennaRNA installed: {_vienna() is not None}")
    if _vienna() is None:
        print("  Running in approximate mode. Install with: pip install ViennaRNA")

    # Known RBS sequences, ordered by how strong they should be.
    # BBa_B0034 is the iGEM standard strong RBS; BBa_B0033 is its weak
    # sibling. A correct calculator must rank them in that order.
    cases = [
        ("perfect SD, optimal spacing",
         "TTCTAGAGAAAGAGGAGAAATACTAGATGAAAGCATTTACC"),
        ("BBa_B0034 (iGEM strong)",
         "TTCTAGAGAAAGAGGAGAAATACTAGATGCGTAAAGGAGAA"),
        ("BBa_B0033 (iGEM weak)",
         "TTCTAGAGTCACACAGGACTACTAGATGCGTAAAGGAGAA"),
        ("no SD motif at all",
         "TTCTAGAGCCCCCCCCCCCCTACTAGATGAAAGCATTTACC"),
        ("SD too far from start",
         "AAAGAGGAGAAACCCCCCCCCCCCCCCCATGAAAGCATTTACC"),
        ("GC-rich, likely folded",
         "GCGCGCGCGGAGGCGCGCGCGCGCGCATGAAAGCATTTACC"),
    ]

    print(f"\n{'sequence':34} {'TIR':>12}  {'dG':>8}  SD motif")
    print("-" * 76)

    results = []
    for label, seq in cases:
        r = calculate_rbs(seq)
        results.append((label, r))
        print(f"{label:34} {r.translation_rate:>12,.0f}  "
              f"{r.dg_total:>+8.2f}  {r.sd_sequence or '(none)'}")

    print("\n" + "-" * 76)
    print("Energy breakdown for the strongest case")
    print("-" * 76)
    best = max(results, key=lambda x: x[1].translation_rate)
    r = best[1]
    print(f"\n  {best[0]}")
    print(f"    dG_mRNA:rRNA  {r.dg_mrna_rrna:>+8.2f}   SD binding to 16S rRNA")
    print(f"    dG_start      {r.dg_start:>+8.2f}   start codon {r.start_codon}")
    print(f"    dG_spacing    {r.dg_spacing:>+8.2f}   gap of {r.spacing} "
          f"(optimal {OPTIMAL_SPACING})")
    print(f"    dG_standby    {r.dg_standby:>+8.2f}   landing pad")
    print(f"    dG_mRNA       {r.dg_mrna:>+8.2f}   cost to unfold")
    print(f"    {'-' * 44}")
    print(f"    dG_total      {r.dg_total:>+8.2f}   -> TIR "
          f"{r.translation_rate:,.0f} ({r.strength})")

    print("\n" + "-" * 76)
    print("Sanity check — does it rank known parts correctly?")
    print("-" * 76)
    strong = next(r for l, r in results if "B0034" in l)
    weak = next(r for l, r in results if "B0033" in l)
    none_sd = next(r for l, r in results if "no SD" in l)

    ok_pair = strong.translation_rate > weak.translation_rate
    ok_none = strong.translation_rate > none_sd.translation_rate

    print(f"\n  B0034 (strong) > B0033 (weak)  : "
          f"{'PASS' if ok_pair else 'FAIL'}  "
          f"{strong.translation_rate:,.0f} vs {weak.translation_rate:,.0f}")
    print(f"  B0034 (strong) > no SD motif   : "
          f"{'PASS' if ok_none else 'FAIL'}  "
          f"{strong.translation_rate:,.0f} vs {none_sd.translation_rate:,.0f}")

    if ok_pair and ok_none:
        print("\n  Ranking is correct. Absolute values depend on the method;")
        print("  ratios between sequences are what matter.")
    else:
        print("\n  Ranking is wrong — the energy model needs checking.")

    print("\n" + "=" * 76)