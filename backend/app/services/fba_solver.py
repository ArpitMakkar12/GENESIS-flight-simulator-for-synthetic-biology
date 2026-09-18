"""FBA solver wrapper around COBRApy.

Loads the iML1515 E. coli metabolic model and solves FBA/FVA
with custom reaction bounds from the BoundCompiler.

Owned by: Arpit
"""

import gzip
import os
from dataclasses import dataclass, field
from pathlib import Path

import cobra
import httpx

from app.services.bound_compiler import ReactionBound


@dataclass
class FBAResult:
    growth_rate: float
    flux_distribution: dict[str, float]
    flux_ranges: dict[str, tuple[float, float]]  # From FVA
    status: str  # 'optimal', 'infeasible', 'unbounded'
    active_pathways: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)


# BiGG model URL (HTTPS, direct download)
MODEL_URL = "https://bigg.ucsd.edu/static/models/iML1515.xml.gz"
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/app/data/models"))
MODEL_PATH = MODEL_DIR / "iML1515.xml.gz"


class FBASolver:
    """Wrapper around COBRApy for Flux Balance Analysis."""

    def __init__(self):
        self.model: cobra.Model | None = None

    def load_model(self) -> None:
        """Load the iML1515 SBML model into COBRApy."""
        if self.model is not None:
            return

        # Download if not present
        if not MODEL_PATH.exists():
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            print(f"  Downloading iML1515 model...", end=" ", flush=True)
            resp = httpx.get(MODEL_URL, follow_redirects=True, timeout=60)
            resp.raise_for_status()
            MODEL_PATH.write_bytes(resp.content)
            print(f"{len(resp.content) / 1e6:.1f} MB")

        # Load — decompress if gzipped
        if str(MODEL_PATH).endswith(".gz"):
            import tempfile
            with gzip.open(MODEL_PATH, "rb") as f_in:
                tmp = Path(tempfile.mktemp(suffix=".xml"))
                tmp.write_bytes(f_in.read())
                self.model = cobra.io.read_sbml_model(str(tmp))
                tmp.unlink()
        else:
            self.model = cobra.io.read_sbml_model(str(MODEL_PATH))

        print(f"  iML1515 loaded: {len(self.model.reactions)} reactions, "
              f"{len(self.model.metabolites)} metabolites, "
              f"{len(self.model.genes)} genes")

    def solve(
        self,
        bounds: list[ReactionBound],
        exchange_constraints: dict[str, tuple[float, float]] | None = None,
    ) -> FBAResult:
        """Run FBA with custom bounds and return results."""
        if self.model is None:
            self.load_model()

        # Work on a copy to avoid mutating the cached model
        model = self.model.copy()

        # Apply expression-derived bounds
        bounds_applied = 0
        for bound in bounds:
            if bound.reaction_id in model.reactions:
                rxn = model.reactions.get_by_id(bound.reaction_id)
                # Only tighten bounds, never loosen
                if bound.upper_bound < rxn.upper_bound:
                    rxn.upper_bound = bound.upper_bound
                if bound.lower_bound > rxn.lower_bound:
                    rxn.lower_bound = bound.lower_bound
                bounds_applied += 1

        # Apply exchange constraints (media composition)
        if exchange_constraints:
            for rxn_id, (lb, ub) in exchange_constraints.items():
                if rxn_id in model.reactions:
                    rxn = model.reactions.get_by_id(rxn_id)
                    rxn.lower_bound = lb
                    rxn.upper_bound = ub

        # Set medium for carbon source (glucose by default)
        # iML1515 uses EX_glc__D_e for glucose exchange
        # Default already set in the model

        # Solve FBA
        solution = model.optimize()

        if solution.status != "optimal":
            return FBAResult(
                growth_rate=0.0,
                flux_distribution={},
                flux_ranges={},
                status=solution.status,
            )

        # Get flux distribution (only non-zero fluxes)
        flux_dist = {
            rxn.id: solution.fluxes[rxn.id]
            for rxn in model.reactions
            if abs(solution.fluxes[rxn.id]) > 1e-6
        }

        # Identify active pathways from our DB (SBML lacks subsystem annotations)
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        from app.config import settings

        pathway_fluxes: dict[str, float] = {}
        engine = create_engine(settings.DATABASE_URL_SYNC)
        with Session(engine) as session:
            rows = session.execute(
                text("SELECT bigg_id, subsystem FROM reactions WHERE subsystem IS NOT NULL AND subsystem != ''")
            ).fetchall()
            rxn_to_subsystem = {row[0]: row[1] for row in rows}

        for rxn_id, flux in flux_dist.items():
            subsystem = rxn_to_subsystem.get(rxn_id, "")
            if subsystem:
                pathway_fluxes[subsystem] = pathway_fluxes.get(subsystem, 0) + abs(flux)
        active_pathways = sorted(pathway_fluxes, key=pathway_fluxes.get, reverse=True)[:15]

        # Identify bottlenecks (reactions at their bounds)
        bottlenecks = []
        for bound in bounds:
            if bound.reaction_id in model.reactions:
                rxn = model.reactions.get_by_id(bound.reaction_id)
                flux = solution.fluxes.get(rxn.id, 0)
                if abs(flux - bound.upper_bound) < 1e-6 or abs(flux - bound.lower_bound) < 1e-6:
                    bottlenecks.append(rxn.id)

        return FBAResult(
            growth_rate=solution.objective_value,
            flux_distribution=flux_dist,
            flux_ranges={},  # FVA can be added later for specific reactions
            status="optimal",
            active_pathways=active_pathways,
            bottlenecks=bottlenecks[:10],
        )
