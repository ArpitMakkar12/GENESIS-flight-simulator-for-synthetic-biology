"""Converts AI expression predictions + BRENDA kinetics into FBA reaction bounds.

This is the bridge between Pillar 2 (AI) and Pillar 3 (FBA).
Formula: flux_bound = relative_expression × reference_tpm × kcat × activity_factor(T, pH) × saturation

Owned by: Arpit
"""
import ast
import logging
import math
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from contracts.interfaces import GeneExpressionResult

logger = logging.getLogger(__name__)


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
UPREGULATION_GAIN = 1.0

# P0 item 3: above this temperature activity collapses on top of the
# Gaussian (factor e^-1 per HEAT_COLLAPSE_SCALE degrees). 46 °C is roughly
# the upper growth limit of E. coli K-12.
HEAT_COLLAPSE_C = 46.0
HEAT_COLLAPSE_SCALE = 1.5


def _parse_gpr(rule: str | None):
    """Parse an iML1515 gene rule like '(b0726 and b0727) or b1276' into an AST node."""
    if not rule or not rule.strip():
        return None
    try:
        return ast.parse(rule, mode="eval").body
    except SyntaxError:
        return None


def _gpr_eval(node, values: dict[str, float]) -> float | None:
    """Combine gene values through a gene rule.

    AND -> min  (subunits of one complex: the scarcest subunit limits)
    OR  -> sum  (isozymes: capacities add)
    Genes with no value are skipped; returns None if nothing is known.
    """
    if isinstance(node, ast.Name):
        return values.get(node.id)
    if isinstance(node, ast.BoolOp):
        vals = [v for v in (_gpr_eval(c, values) for c in node.values) if v is not None]
        if not vals:
            return None
        return min(vals) if isinstance(node.op, ast.And) else sum(vals)
    return None


class BoundCompiler:
    """Converts AI expression predictions + BRENDA kinetics into FBA reaction bounds.

    This is the bridge between Pillar 2 (AI) and Pillar 3 (FBA).
    """

    def __init__(self):
        self._kinetics_cache: dict[str, dict] = {}
        self._gene_reaction_map: dict[str, list[str]] = {}
        self._gpr_trees: dict[str, ast.AST | None] | None = None
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

    def set_gpr_rules(self, gpr_rules: dict[str, str]) -> None:
        """Store the gene rules once, e.g. {r.id: r.gene_reaction_rule for r in model.reactions}."""
        self._gpr_trees = {rid: _parse_gpr(rule) for rid, rule in gpr_rules.items()}

    def compile(
        self,
        expression_results: list[GeneExpressionResult],
        temperature: float,
        ph: float,
        gpr_rules: dict[str, str] | None = None,
    ) -> list[ReactionBound]:
        """Compile FBA bounds from expression predictions and enzyme kinetics.

        Builds ONE bound per reaction. Genes are combined through the
        reaction's gene rule (AND -> min, OR -> sum). Previously the per-gene
        caps were merged with min(), so for isozymes (ACONTb <- acnA OR acnB)
        the lower-expressed gene set the cap (acnA 178 TPM vs acnB 1,644 TPM),
        which held reference growth at 0.29 instead of ~0.8.

        If no gene rules have been supplied, falls back to the old min() rule.
        """
        self._load_data()

        if gpr_rules is not None:
            self.set_gpr_rules(gpr_rules)
        if self._gpr_trees is None:
            logger.warning("BoundCompiler.compile: no gpr_rules supplied - using legacy min() over genes")
        gpr_trees = self._gpr_trees or {}

        # Pass 1: per-gene clamped expression, reference anchor, reactions touched
        rel_by_gene: dict[str, float] = {}
        tpm_by_gene: dict[str, float] = {}
        genes_by_rxn: dict[str, list[str]] = {}

        for result in expression_results:
            gene_id = result.gene_id
            raw_expr = result.relative_expression
            ref_tpm = result.reference_expression_tpm or 100.0

            # ── P0 FIX: Clamp the upside ──
            # Downregulation (raw_expr < 1.0) tightens bounds as before —
            # a repressed gene genuinely limits flux.
            # Upregulation (raw_expr > 1.0) is damped by UPREGULATION_GAIN:
            # FBA does not model the protein cost of making more enzyme, so
            # unclamped upregulation would loosen bounds for free.
            if raw_expr <= 1.0:
                rel_expr = raw_expr
            else:
                rel_expr = 1.0 + math.log2(raw_expr) * UPREGULATION_GAIN

            rel_by_gene[gene_id] = rel_expr
            tpm_by_gene[gene_id] = ref_tpm
            for rxn_id in self._gene_reaction_map.get(gene_id, []):
                genes_by_rxn.setdefault(rxn_id, []).append(gene_id)

        amount_now = {g: rel_by_gene[g] * tpm_by_gene[g] for g in rel_by_gene}

        # Pass 2: one bound per reaction, genes combined through the gene rule
        bounds: dict[str, ReactionBound] = {}
        for rxn_id, genes in genes_by_rxn.items():
            tree = gpr_trees.get(rxn_id)
            now = ref = None
            if tree is not None:
                now = _gpr_eval(tree, amount_now)   # enzyme amount in this condition
                ref = _gpr_eval(tree, tpm_by_gene)  # enzyme amount at reference
            if now is None or not ref:
                # Legacy behaviour: the weakest catalysing gene sets the cap
                now = min(amount_now[g] for g in genes)
                rel_rxn = min(rel_by_gene[g] for g in genes)
                rule_tag = "min"
            else:
                rel_rxn = now / ref
                rule_tag = "gpr"

            kinetics = self._kinetics_cache.get(rxn_id)
            if kinetics:
                activity = self.get_activity_factor(
                    kinetics["optimal_temp"],
                    kinetics["optimal_ph"],
                    temperature,
                    ph,
                )
                # flux_max = enzyme amount (expression × tpm) × kcat × activity × scale
                flux_max = now * kinetics["kcat"] * activity * EXPRESSION_TO_FLUX_SCALE
                source = f"expression+kinetics+{rule_tag}"
            else:
                # Expression-only: scale default bounds by relative capacity
                flux_max = DEFAULT_UPPER * rel_rxn
                source = f"expression+{rule_tag}"

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