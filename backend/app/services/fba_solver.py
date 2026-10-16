"""FBA solver wrapper around COBRApy.

Loads the iML1515 E. coli metabolic model and solves FBA/FVA
with custom reaction bounds from the BoundCompiler.

Owned by: Arpit
"""

import gzip
import os
import pickle
import threading
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
# The model as COBRApy holds it in memory, saved once with pickle. The
# COBRApy version is in the name: a pickle is only safe to read with the
# version that wrote it (and only one we wrote ourselves).
FAST_COPY_PATH = MODEL_DIR / f"iML1515-cobra{cobra.__version__}.pkl"


class FBASolver:
    """Wrapper around COBRApy for Flux Balance Analysis."""

    def __init__(self):
        self.model: cobra.Model | None = None
        self._lock = threading.Lock()                  # one solve at a time on the shared model
        self._subsystems: dict[str, str] | None = None  # reaction -> pathway name, read once

    def load_model(self) -> None:
        """Load iML1515, always from the pickled copy (made from the SBML on first use).

        Why always the pickle: it loads in ~0.5 s instead of ~3 s (10x that
        on 0.1 CPU), needs ~120 MB less memory, and every machine then solves
        the very same model. A freshly parsed SBML and its pickle can pick
        different, equally good flux patterns for the same input.
        """
        if self.model is not None:
            return
        if not FAST_COPY_PATH.exists():
            self._save_fast_copy()
        with open(FAST_COPY_PATH, "rb") as f:
            self.model = pickle.load(f)
        print(f"  iML1515 loaded: {len(self.model.reactions)} reactions, "
              f"{len(self.model.metabolites)} metabolites, "
              f"{len(self.model.genes)} genes")

    def _save_fast_copy(self) -> None:
        """Download the SBML if needed, parse it once, and save the pickle."""
        if not MODEL_PATH.exists():
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            print(f"  Downloading iML1515 model...", end=" ", flush=True)
            resp = httpx.get(MODEL_URL, follow_redirects=True, timeout=60)
            resp.raise_for_status()
            MODEL_PATH.write_bytes(resp.content)
            print(f"{len(resp.content) / 1e6:.1f} MB")

        print("  Parsing the SBML model once (about 3 s)...", flush=True)
        with gzip.open(MODEL_PATH, "rb") as f_in:
            tmp = MODEL_DIR / "iML1515.parsing.xml"
            tmp.write_bytes(f_in.read())
        model = cobra.io.read_sbml_model(str(tmp))
        tmp.unlink()

        # Write to a temporary name first, so a crash never leaves half a file
        part = FAST_COPY_PATH.with_suffix(".part")
        with open(part, "wb") as f:
            pickle.dump(model, f)
        os.replace(part, FAST_COPY_PATH)
        print(f"  Saved {FAST_COPY_PATH.name}")

    def gene_ids(self) -> set[str]:
        """Locus tags of every gene in the metabolic model (e.g. 'b0903')."""
        if self.model is None:
            self.load_model()
        return {g.id for g in self.model.genes}

    def solve(
        self,
        bounds: list[ReactionBound],
        exchange_constraints: dict[str, tuple[float, float]] | None = None,
        knockout_genes: list[str] | None = None,
    ) -> FBAResult:
        """Run FBA with custom bounds and return results.

        knockout_genes: locus tags to delete. COBRApy reads each reaction's
        gene rule, so a reaction stops only if no backup gene (isozyme) can
        still run it.
        """
        if self.model is None:
            self.load_model()

        # Every change made inside "with self.model" (bounds, knockouts) is
        # undone when the block ends, even after an error, so the shared model
        # is never altered. This replaces model.copy(), which took ~0.7 s of
        # CPU and a second copy of the model in memory: 95% of each solve.
        # The lock stops two requests from changing the shared model at once.
        with self._lock, self.model as model:
            return self._solve(model, bounds, exchange_constraints, knockout_genes)

    def _subsystem_map(self) -> dict[str, str]:
        """Reaction -> pathway name, read from the database once and kept."""
        if self._subsystems is None:
            from sqlalchemy import create_engine, text
            from app.config import settings

            engine = create_engine(settings.DATABASE_URL_SYNC)
            with engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT bigg_id, subsystem FROM reactions WHERE subsystem IS NOT NULL AND subsystem != ''")
                ).fetchall()
            engine.dispose()
            self._subsystems = {row[0]: row[1] for row in rows}
        return self._subsystems

    @staticmethod
    def _fresh_start(model) -> None:
        """Make GLPK forget the last solution (reset to its standard starting basis)."""
        try:
            import swiglpk
            swiglpk.glp_std_basis(model.solver.problem)
        except (ImportError, AttributeError, TypeError):
            pass  # a solver other than GLPK: nothing to reset

    def _solve(self, model, bounds, exchange_constraints, knockout_genes) -> FBAResult:
        # Gene knockouts go first: they close reactions completely, and the
        # bounds below can only tighten, never reopen them.
        for gene_id in knockout_genes or []:
            model.genes.get_by_id(gene_id).knock_out()

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

        # Solve FBA, starting the solver from the same point every time.
        # Often several flux patterns give the same top growth; on a shared
        # model the solver would carry on from the previous request and pick
        # a different one each time. Starting fresh keeps runs reproducible.
        self._fresh_start(model)
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
        pathway_fluxes: dict[str, float] = {}
        rxn_to_subsystem = self._subsystem_map()

        for rxn_id, flux in flux_dist.items():
            subsystem = rxn_to_subsystem.get(rxn_id, "")
            # F10: 'Unassigned' is a placeholder, not a pathway
            if subsystem and subsystem.strip().lower() not in ("unassigned", "none"):
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

        # F9: an uptake limit (e.g. carbon or O2 exchange pinned at its lower
        # bound) is a real growth limit and should not be hidden.
        if exchange_constraints:
            for rxn_id, (lb, _ub) in exchange_constraints.items():
                if lb >= 0 or rxn_id not in model.reactions:
                    continue
                flux = solution.fluxes.get(rxn_id, 0)
                if abs(flux - lb) < 1e-6:
                    bottlenecks.insert(0, rxn_id)

        return FBAResult(
            growth_rate=solution.objective_value,
            flux_distribution=flux_dist,
            flux_ranges={},  # FVA can be added later for specific reactions
            status="optimal",
            active_pathways=active_pathways,
            bottlenecks=bottlenecks[:10],
        )

    def solver_name(self) -> str:
        """Name of the LP solver COBRApy is using (F5)."""
        if self.model is None:
            self.load_model()
        try:
            return self.model.solver.interface.__name__.split(".")[-1].replace("_interface", "")
        except Exception:
            return "unknown"

    @staticmethod
    def cobra_version() -> str:
        return getattr(cobra, "__version__", "unknown")