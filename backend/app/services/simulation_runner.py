"""Orchestrates the full BioSandbox simulation pipeline.

Pipeline: resolve TFs → predict expression → compile bounds → solve FBA → assemble results

Owned by: Arpit
"""

import sys
import os
import time
import math
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from contracts.interfaces import PredictionInput, PredictionOutput
from app.services.tf_resolver import TFResolver, ENVIRONMENT_RULES
from app.services.bound_compiler import BoundCompiler
from app.services.fba_solver import FBASolver

# Growth rate under the reference condition (37 C, pH 7, aerobic, glucose,
# ammonium). growth_state is reported relative to this.
REFERENCE_GROWTH_RATE = 0.802


class SimulationRunner:
    """Orchestrates the full BioSandbox simulation pipeline.

    Pipeline: resolve TFs → predict expression → compile bounds → solve FBA → results
    """

    def __init__(self):
        self.tf_resolver = TFResolver()
        self.bound_compiler = BoundCompiler()
        self.fba_solver = FBASolver()
        self._predictor = None

    def _get_predictor(self):
        """Lazy-load the predictor to avoid import issues."""
        if self._predictor is None:
            from ai.inference.predictor import EcoliExpressionPredictor
            self._predictor = EcoliExpressionPredictor()
        return self._predictor

    async def run(
        self,
        construct_id: UUID | None,
        raw_sequence: str | None,
        temperature: float,
        ph: float,
        oxygen_level: str,
        carbon_source: str,
        nitrogen_source: str,
        gene_ids: list[str] | None = None,
        gene_sequences: list[str] | None = None,
    ) -> dict:
        """Execute the full simulation pipeline."""
        start_time = time.time()

        # ── Step 1: Resolve TF activation states ──
        tf_states = await self.tf_resolver.resolve(
            temperature=temperature,
            ph=ph,
            oxygen_level=oxygen_level,
            carbon_source=carbon_source,
            nitrogen_source=nitrogen_source,
        )
        tf_activation = {
            name: state.is_active for name, state in tf_states.items()
        }
        active_tfs = [name for name, state in tf_states.items() if state.is_active]

        # ── Step 2: Prepare prediction input ──
        if gene_ids is None or gene_sequences is None:
            # Query all genes that are (a) linked to metabolic reactions and
            # (b) have measured expression. This lets the AI layer constrain
            # most of the metabolic model instead of just 3 reactions.
            # Empty sequences are deliberate — every one of these genes is
            # known, so the predictor resolves them by ID (lookup path,
            # sub-millisecond) and never reads the DNA.
            from sqlalchemy import create_engine, text as sa_text
            from app.config import settings as app_settings

            engine = create_engine(app_settings.DATABASE_URL_SYNC)
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT DISTINCT g.locus_tag FROM genes g "
                    "JOIN enzyme_reactions er ON er.gene_id = g.id "
                    "WHERE g.reference_expression_tpm IS NOT NULL"
                )).fetchall()

            if rows:
                gene_ids = [r[0] for r in rows]
                gene_sequences = [""] * len(gene_ids)
            else:
                # Fallback: if the join table is empty, use minimal set
                gene_ids = ["b0002", "b0344", "b3702"]
                gene_sequences = [""] * len(gene_ids)

        # Custom DNA from the Simulate page. Predicted alongside the genome so
        # the sequence model (Track B) actually reads it. It is not linked to
        # any reaction, so it cannot change growth.
        custom_part_id = None
        if raw_sequence and raw_sequence.strip():
            custom_part_id = "custom_part_1"
            custom_seq = "".join(raw_sequence.split()).upper()  # drop pasted line breaks
            gene_ids = list(gene_ids) + [custom_part_id]
            gene_sequences = list(gene_sequences) + [custom_seq]

        prediction_input = PredictionInput(
            gene_ids=gene_ids,
            gene_sequences=gene_sequences,
            tf_activation=tf_activation,
            temperature=temperature,
            ph=ph,
            oxygen=oxygen_level,
            carbon_source=carbon_source,
            nitrogen_source=nitrogen_source,
        )

        # ── Step 3: Predict expression ──
        predictor = self._get_predictor()
        prediction_output: PredictionOutput = predictor.predict(prediction_input)

        # ── Step 4: Compile bounds ──
        # Gene rules (AND -> min, OR -> sum) so isozymes add up instead of the
        # weakest gene capping the reaction. Loaded once, then cached.
        if self.bound_compiler._gpr_trees is None:
            self.fba_solver.load_model()
            self.bound_compiler.set_gpr_rules(
                {r.id: r.gene_reaction_rule for r in self.fba_solver.model.reactions}
            )

        bounds = self.bound_compiler.compile(
            expression_results=prediction_output.results,
            temperature=temperature,
            ph=ph,
        )

        # ── Step 5: Set exchange constraints based on carbon source ──
        # Kept unscaled for the V7 diagnosis (37 °C, pH 7 uptake capacity).
        base_exchange_constraints = self._get_exchange_constraints(carbon_source, oxygen_level)

        # Uptake is enzyme-mediated (PTS, transporters), so it slows with T and pH
        # like the rest of metabolism. Factor = 1.0 at 37 °C, pH 7.
        uptake_activity = BoundCompiler.get_activity_factor(37.0, 7.0, temperature, ph)
        exchange_constraints = {
            rxn: (lb * uptake_activity if lb < 0 else lb, ub)
            for rxn, (lb, ub) in base_exchange_constraints.items()
        }

        # ── Step 6: Solve FBA ──
        fba_result = self.fba_solver.solve(
            bounds=bounds,
            exchange_constraints=exchange_constraints,
        )

        # ── Step 7: Assemble results ──
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Compute doubling time from growth rate
        doubling_time = None
        if fba_result.growth_rate > 0:
            doubling_time = math.log(2) / fba_result.growth_rate  # hours

        # Build full expression list for persistence, but limit API response
        # to the top 50 most-changed genes to keep responses lean
        all_predictions = [
            {
                "gene_id": r.gene_id,
                "relative_expression": r.relative_expression,
                "confidence": r.confidence,
                "prediction_source": r.prediction_source,
                "rbs_score": r.rbs_score,
                "reference_tpm": r.reference_expression_tpm,
            }
            for r in prediction_output.results
        ]

        # B9: return the top up- and down-regulated genes separately, so
        # repressed genes are not pushed out of the payload by induced ones.
        # Ties within a fold tier are broken by reference_tpm (most
        # abundant first), which surfaces the biologically loudest genes.
        def _tpm(p: dict) -> float:
            return p.get("reference_tpm") or 0.0

        up_all = [p for p in all_predictions if p["relative_expression"] > 1.01]
        down_all = [p for p in all_predictions if p["relative_expression"] < 0.99]

        # Each direction gets at least 25 slots; unused slots go to the
        # other direction so the total stays near 50.
        n_up = max(25, 50 - min(25, len(down_all)))
        n_down = max(25, 50 - min(25, len(up_all)))

        upregulated = sorted(
            up_all, key=lambda p: (-p["relative_expression"], -_tpm(p))
        )[:n_up]
        downregulated = sorted(
            down_all, key=lambda p: (p["relative_expression"], -_tpm(p))
        )[:n_down]
        top_predictions = upregulated + downregulated

        
        # The custom part is the whole point of a run that supplied DNA, so it
        # is always returned — its fold change is 1.0 (no TF targets it), which
        # the up/down filters above would otherwise drop.
        if custom_part_id is not None and not any(
            p["gene_id"] == custom_part_id for p in top_predictions
        ):
            top_predictions = [
                p for p in all_predictions if p["gene_id"] == custom_part_id
            ] + top_predictions

        # B1: the solver status says whether FBA found a solution; it says
        # nothing about how the cell is doing. growth_state is computed
        # against the reference growth rate so the UI can show it directly.
        growth_state = self._growth_state(fba_result.status, fba_result.growth_rate)

        # V7: on an infeasible result, find out why. Only runs on failures.
        #   1) Medium alone at normal uptake, no GENESIS bounds -> fails: biological
        #   2) Medium with this T/pH applied to uptake         -> fails: environmental
        #   3) Otherwise the expression/kinetic bounds caused it -> constraint
        infeasibility_reason = None
        if fba_result.status != "optimal" or fba_result.growth_rate < 0.01:
            baseline = self.fba_solver.solve(
                bounds=[], exchange_constraints=base_exchange_constraints,
            )
            if baseline.status != "optimal" or baseline.growth_rate < 0.01:
                infeasibility_reason = (
                    "biological: the medium cannot support growth even without "
                    "expression or kinetic constraints (e.g. no usable electron "
                    "acceptor for this carbon source)"
                )
            else:
                env_only = self.fba_solver.solve(
                    bounds=[], exchange_constraints=exchange_constraints,
                )
                if env_only.status != "optimal" or env_only.growth_rate < 0.01:
                    infeasibility_reason = (
                        f"environmental: at {temperature:g} °C, pH {ph:g}, enzyme and "
                        f"uptake activity ({uptake_activity:.0%} of optimum) fall below "
                        "the cell's maintenance-energy requirement"
                    )
                else:
                    infeasibility_reason = (
                        "constraint: growth is possible on this medium "
                        f"({env_only.growth_rate:.4f} hr-1 without GENESIS bounds), so the "
                        "expression/kinetic bounds applied by GENESIS caused the failure"
                    )

        # B4: report the master regulators explicitly (the full active list
        # is dominated by ~350 default-active TFs and truncating it hid CRP).
        master = {name.lower(): name for name in ENVIRONMENT_RULES}
        regulator_state = {
            master[name.lower()]: state.is_active
            for name, state in tf_states.items()
            if name.lower() in master
        }
        meta = prediction_output.metadata or {}
        active_masters = [n for n, on in regulator_state.items() if on]
        others = [n for n in active_tfs if n.lower() not in master]

        return {
            "solver_status": fba_result.status,
            "growth_state": growth_state,
            "infeasibility_reason": infeasibility_reason,
            "growth_rate": round(fba_result.growth_rate, 4),
            "doubling_time": round(doubling_time, 2) if doubling_time else None,
            "viability_score": self._viability(fba_result.growth_rate, temperature),
            "active_pathways": fba_result.active_pathways,
            "bottlenecks": fba_result.bottlenecks,
            "expression_predictions": top_predictions,
            "expression_all": all_predictions,
            # B5: changed-gene counts, split by direction
            "expression_summary": {
                "total_genes_evaluated": len(all_predictions),
                "genes_with_changed_expression": len(up_all) + len(down_all),
                "genes_up": len(up_all),
                "genes_down": len(down_all),
                "genes_by_source": meta.get("genes_by_source"),
                "model_error": meta.get("model_error"),
                "validation_warnings": meta.get("validation_warnings"),
                "custom_sequence_bp": len(gene_sequences[-1]) if custom_part_id else None,
            },
            # B3: flux values from the COBRApy solution (already filtered to
            # |flux| > 1e-6 by the solver); all non-zero fluxes (~450) so small
            # but important ones (e.g. ICL/MALS on acetate) are not dropped
            "flux_distribution": {
                rxn_id: round(flux, 6)
                for rxn_id, flux in sorted(
                    fba_result.flux_distribution.items(),
                    key=lambda x: abs(x[1]),
                    reverse=True,
                )
            },
            "flux_summary": {
                "total_reactions_with_flux": len(fba_result.flux_distribution),
                "bounds_applied": len(bounds),
            },
            "active_tfs": active_masters + others[: max(0, 20 - len(active_masters))],
            "regulator_state": regulator_state,
            "tf_state_changes": meta.get("tf_state_changes", {}),
            "model_version": prediction_output.model_version,
            # F5: every model in the pipeline, not just the predictor
            "model_versions": {
                "predictor": prediction_output.model_version,
                "metabolic_model": "iML1515",
                "solver": self.fba_solver.solver_name(),
                "cobra": self.fba_solver.cobra_version(),
            },
            "compute_time_ms": elapsed_ms,
            "conditions": {
                "temperature": temperature,
                "ph": ph,
                "oxygen": oxygen_level,
                "carbon_source": carbon_source,
                "nitrogen_source": nitrogen_source,
            },
        }

    @staticmethod
    def _viability(growth_rate: float, temperature: float) -> float:
        """Cell viability score [0-1].

        Above ~46 °C E. coli K-12 loses viability rapidly even if FBA can
        still find flux routes, so we drop the score with temperature.
        """
        if growth_rate < 0.01:
            return 0.0
        if temperature >= 50.0:
            return 0.1
        if temperature >= 48.0:
            return 0.4
        if temperature >= 46.0:
            return 0.7
        return 1.0

    @staticmethod
    def _growth_state(solver_status: str, growth_rate: float) -> str:
        """Classify growth relative to the wild-type reference condition."""
        if solver_status != "optimal" or growth_rate < 0.01:
            return "not-viable"
        ratio = growth_rate / REFERENCE_GROWTH_RATE
        if ratio >= 0.9:
            return "optimal"
        if ratio >= 0.5:
            return "slowed"
        return "stressed"

    @staticmethod
    def _get_exchange_constraints(
        carbon_source: str,
        oxygen_level: str,
    ) -> dict[str, tuple[float, float]]:
        """Set exchange reaction bounds based on media composition."""
        constraints: dict[str, tuple[float, float]] = {}

        # Carbon source exchange reactions
        carbon_exchanges = {
            "glucose": "EX_glc__D_e",
            "lactose": "EX_lcts_e",
            "glycerol": "EX_glyc_e",
            "acetate": "EX_ac_e",
            "succinate": "EX_succ_e",
            "fructose": "EX_fru_e",
            "galactose": "EX_gal_e",
            "xylose": "EX_xyl__D_e",
            "arabinose": "EX_arab__L_e",
        }

        # Every carbon source gets the same carbon supply: 60 C-mmol/gDW/h,
        # i.e. the standard 10 mmol/gDW/h of glucose. Without this, a 12-carbon
        # sugar (lactose) delivers twice the carbon of glucose and out-grows it.
        CARBON_ATOMS = {
            "glucose": 6, "fructose": 6, "galactose": 6, "lactose": 12,
            "glycerol": 3, "acetate": 2, "succinate": 4,
            "xylose": 5, "arabinose": 5,
        }
        CARBON_UPTAKE_CMMOL = 60.0

        # Turn off all carbon sources first, then enable the selected one
        for source, rxn_id in carbon_exchanges.items():
            if source == carbon_source:
                uptake = CARBON_UPTAKE_CMMOL / CARBON_ATOMS[source]
                constraints[rxn_id] = (-uptake, 1000.0)  # uptake allowed
            else:
                constraints[rxn_id] = (0.0, 1000.0)      # no uptake

        # Oxygen
        if oxygen_level == "aerobic":
            constraints["EX_o2_e"] = (-20.0, 1000.0)
            # F2: pyruvate formate-lyase is irreversibly inactivated by O2
            # (its glycyl radical is cleaved), so it carries no flux in
            # aerobically growing cells. The solver applies this like any
            # other bound because PFL is a model reaction.
            constraints["PFL"] = (0.0, 0.0)
        elif oxygen_level == "microaerobic":
            constraints["EX_o2_e"] = (-2.0, 1000.0)
        elif oxygen_level == "anaerobic":
            constraints["EX_o2_e"] = (0.0, 1000.0)

        return constraints
