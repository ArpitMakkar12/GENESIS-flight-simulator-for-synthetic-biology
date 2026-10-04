"""Converts AI expression predictions + BRENDA kinetics into FBA reaction bounds.

This is the bridge between Pillar 2 (AI) and Pillar 3 (FBA).
Formula: flux_bound = relative_expression × reference_tpm × kcat × activity_factor(T, pH) × saturation

Owned by: Arpit
"""

import math
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from contracts.interfaces import GeneExpressionResult


@dataclass
class ReactionBound:
    reaction_id: str       # BiGG reaction ID
    lower_bound: float
    upper_bound: float
    source: str            # 'expression', 'kinetics', 'transport', 'default'


# Scaling factor to convert TPM × kcat into flux units (mmol/gDW/hr)
# This accounts for: mRNA → protein translation, protein per cell, cell mass
# Calibrated so reference conditions reproduce wild-type iML1515 growth rate
EXPRESSION_TO_FLUX_SCALE = 1e-4

# Default bounds when no kinetics data is available
DEFAULT_LOWER = -1000.0
DEFAULT_UPPER = 1000.0

# P0 interim clamp (see "Simulation Test Report & Fix List", P0 item 2).
# How much of an upregulation is allowed to loosen a flux bound, applied as
#     effective = 1.0 + log2(relative_expression) * UPREGULATION_GAIN
# 0.0 ignores upregulation entirely; 1.0 would be close to the old,
# uncapped behaviour. Downregulation (< 1.0) is never damped.
# Remove once the proteome-allocation constraint (P0 item 1) lands.
UPREGULATION_GAIN = 0.0

# P0 item 3: above this temperature activity collapses on top of the
# Gaussian (factor e^-1 per HEAT_COLLAPSE_SCALE degrees). 46 °C is roughly
# the upper growth limit of E. coli K-12.
HEAT_COLLAPSE_C = 46.0
HEAT_COLLAPSE_SCALE = 1.5


class BoundCompiler:
    """Converts AI expression predictions + BRENDA kinetics into FBA reaction bounds.

    This is the bridge between Pillar 2 (AI) and Pillar 3 (FBA).
    """

    def __init__(self):
        self._kinetics_cache: dict[str, dict] = {}
        self._gene_reaction_map: dict[str, list[str]] = {}
        self._loaded = False

    def _load_data(self) -> None:
        """Load kinetics and gene-reaction mappings from DB."""
        if self._loaded:
            return

        engine = create_engine(settings.DATABASE_URL_SYNC)
        with Session(engine) as session:
            # Load kinetics: EC number -> {kcat, km, optimal_temp, optimal_ph}
            rows = session.execute(text("""
                SELECT r.bigg_id, ek.kcat_value, ek.km_value,
                       ek.optimal_temp, ek.optimal_ph
                FROM enzyme_kinetics ek
                JOIN reactions r ON ek.reaction_id = r.id
                WHERE ek.kcat_value IS NOT NULL
            """)).fetchall()
            for bigg_id, kcat, km, opt_temp, opt_ph in rows:
                self._kinetics_cache[bigg_id] = {
                    "kcat": kcat,
                    "km": km,
                    "optimal_temp": opt_temp or 37.0,
                    "optimal_ph": opt_ph or 7.0,
                }

            # Load gene -> reaction mappings
            rows = session.execute(text("""
                SELECT g.locus_tag, r.bigg_id
                FROM enzyme_reactions er
                JOIN genes g ON er.gene_id = g.id
                JOIN reactions r ON er.reaction_id = r.id
            """)).fetchall()
            for locus_tag, bigg_id in rows:
                if locus_tag not in self._gene_reaction_map:
                    self._gene_reaction_map[locus_tag] = []
                self._gene_reaction_map[locus_tag].append(bigg_id)

        self._loaded = True

    def compile(
        self,
        expression_results: list[GeneExpressionResult],
        temperature: float,
        ph: float,
    ) -> list[ReactionBound]:
        """Compile FBA bounds from expression predictions and enzyme kinetics."""
        self._load_data()

        bounds: dict[str, ReactionBound] = {}

        for result in expression_results:
            gene_id = result.gene_id
            raw_expr = result.relative_expression
            ref_tpm = result.reference_expression_tpm or 100.0

            # ── P0 FIX: Clamp the upside ──
            # Downregulation (raw_expr < 1.0) tightens bounds as before —
            # a repressed gene genuinely limits flux.
            # Upregulation (raw_expr > 1.0) is dampened: the cell cannot
            # benefit from producing more enzyme without paying a protein
            # synthesis cost, which FBA does not model. Without this clamp,
            # any condition that activates many genes (lactose, heat shock)
            # loosens bounds and raises growth above reference, producing
            # the paradox where a stressed cell outgrows a healthy one.
            #
            # The dampened form: 1.0 + log2(raw) * 0.1
            # — a 2× upregulation adds only 10% capacity
            # — a 4× upregulation adds only 20% capacity
            # — downregulation below 1.0 is unchanged
            if raw_expr <= 1.0:
                rel_expr = raw_expr
            else:
                rel_expr = 1.0 + math.log2(raw_expr) * UPREGULATION_GAIN

            # Find reactions catalyzed by this gene
            reactions = self._gene_reaction_map.get(gene_id, [])
            if not reactions:
                continue

            for rxn_id in reactions:
                # Get kinetics if available
                kinetics = self._kinetics_cache.get(rxn_id)

                if kinetics:
                    # Full calculation with kinetics
                    kcat = kinetics["kcat"]
                    activity = self.get_activity_factor(
                        kinetics["optimal_temp"],
                        kinetics["optimal_ph"],
                        temperature,
                        ph,
                    )

                    # flux_max = expression × tpm_anchor × kcat × activity × scale
                    flux_max = rel_expr * ref_tpm * kcat * activity * EXPRESSION_TO_FLUX_SCALE
                    source = "expression+kinetics"
                else:
                    # Expression-only: scale default bounds by expression level
                    flux_max = DEFAULT_UPPER * rel_expr
                    source = "expression"

                # Keep the tightest bound if multiple genes map to same reaction.
                # V3 note: for isozymes (e.g. ACONTb <- acnA OR acnB) this means
                # the LOWER-expressed gene sets the cap (acnA, 178 TPM, rather
                # than acnB, 1,644 TPM). Summing isozyme capacity would be more
                # faithful, but it changes the baseline calibration and belongs
                # with P0 item 4, after the proteome-allocation constraint.
                if rxn_id in bounds:
                    existing = bounds[rxn_id]
                    bounds[rxn_id] = ReactionBound(
                        reaction_id=rxn_id,
                        # tightest reverse limit = the least negative one
                        lower_bound=max(existing.lower_bound, -flux_max),
                        upper_bound=min(existing.upper_bound, flux_max),
                        source=source,
                    )
                else:
                    bounds[rxn_id] = ReactionBound(
                        reaction_id=rxn_id,
                        lower_bound=-flux_max,
                        upper_bound=flux_max,
                        source=source,
                    )

        return list(bounds.values())

    @staticmethod
    def get_activity_factor(
        opt_temp: float,
        opt_ph: float,
        actual_temp: float,
        actual_ph: float,
    ) -> float:
        """Get enzyme activity scaling factor at given T and pH.

        Uses Gaussian-like decay from optimum. At optimum = 1.0,
        decreases with distance from optimum.

        Note on pH: opt_ph is per-reaction (BRENDA). The growth-limiting
        reaction under respiration, ACONTb, has opt_ph = 7.4, which is why
        the effective whole-cell curve peaks near pH 7.4 rather than 7.0
        and why pH 8.5 retains more activity than pH 5.5 (V6/D2).
        """
        # Temperature: sigma ~= 10°C (enzyme stability range)
        temp_factor = math.exp(-0.5 * ((actual_temp - opt_temp) / 10.0) ** 2)

        # P0 item 3: thermal collapse. Enzyme activity is not symmetric
        # about the optimum — above ~46 °C E. coli proteins denature and the
        # cell stops growing, while the Gaussian alone still leaves ~43% at
        # 50 °C. Apply an additional exponential decay above HEAT_COLLAPSE_C.
        if actual_temp > HEAT_COLLAPSE_C:
            temp_factor *= math.exp(-(actual_temp - HEAT_COLLAPSE_C) / HEAT_COLLAPSE_SCALE)

        # pH: sigma ~= 1.5 pH units
        ph_factor = math.exp(-0.5 * ((actual_ph - opt_ph) / 1.5) ** 2)

        return temp_factor * ph_factor
