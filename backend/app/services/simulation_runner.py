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
from app.services.tf_resolver import TFResolver
from app.services.bound_compiler import BoundCompiler
from app.services.fba_solver import FBASolver


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
            # Default: use a representative set of iML1515 genes
            gene_ids = gene_ids or ["b0002", "b0344", "b3702"]
            gene_sequences = gene_sequences or ["ATGC" * 200] * len(gene_ids)

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
        bounds = self.bound_compiler.compile(
            expression_results=prediction_output.results,
            temperature=temperature,
            ph=ph,
        )

        # ── Step 5: Set exchange constraints based on carbon source ──
        exchange_constraints = self._get_exchange_constraints(carbon_source, oxygen_level)

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

        return {
            "status": fba_result.status,
            "growth_rate": round(fba_result.growth_rate, 4),
            "doubling_time": round(doubling_time, 2) if doubling_time else None,
            "viability_score": 1.0 if fba_result.growth_rate > 0.01 else 0.0,
            "active_pathways": fba_result.active_pathways,
            "bottlenecks": fba_result.bottlenecks,
            "expression_predictions": [
                {
                    "gene_id": r.gene_id,
                    "relative_expression": r.relative_expression,
                    "confidence": r.confidence,
                    "prediction_source": r.prediction_source,
                    "reference_tpm": r.reference_expression_tpm,
                }
                for r in prediction_output.results
            ],
            "flux_summary": {
                "total_reactions_with_flux": len(fba_result.flux_distribution),
                "bounds_applied": len(bounds),
            },
            "active_tfs": active_tfs[:20],
            "model_version": prediction_output.model_version,
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

        # Turn off all carbon sources first, then enable the selected one
        for source, rxn_id in carbon_exchanges.items():
            if source == carbon_source:
                constraints[rxn_id] = (-10.0, 1000.0)  # uptake allowed
            else:
                constraints[rxn_id] = (0.0, 1000.0)    # no uptake

        # Oxygen
        if oxygen_level == "aerobic":
            constraints["EX_o2_e"] = (-20.0, 1000.0)
        elif oxygen_level == "microaerobic":
            constraints["EX_o2_e"] = (-2.0, 1000.0)
        elif oxygen_level == "anaerobic":
            constraints["EX_o2_e"] = (0.0, 1000.0)

        return constraints
