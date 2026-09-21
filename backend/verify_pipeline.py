"""Sensitivity test — does gene expression actually change the growth rate?

Run inside the backend container:
    docker compose exec backend python verify_pipeline.py

THE QUESTION
------------
The AI layer's whole job is to say how active each gene is. That number
travels: predictor -> bound compiler -> FBA solver -> growth rate.

Nobody has checked whether it survives that journey. This script feeds
the pipeline expression values from 0.001 (everything switched off) to
100 (everything blasting) and watches what the growth rate does.

    If growth barely moves, the AI layer has no effect on the answer,
    and training a model would change nothing until that is fixed.

Read-only. Changes nothing.
"""

import asyncio
import traceback

from sqlalchemy import create_engine, text

from app.config import settings
from app.services.bound_compiler import BoundCompiler
from app.services.fba_solver import FBASolver
from app.services.tf_resolver import TFResolver
from contracts.interfaces import GeneExpressionResult

engine = create_engine(settings.DATABASE_URL_SYNC)


def section(title):
    print(f"\n{'=' * 66}\n{title}\n{'=' * 66}")


def load_genes(limit=None):
    sql = ("SELECT locus_tag, reference_expression_tpm FROM genes "
           "WHERE reference_expression_tpm IS NOT NULL")
    if limit:
        sql += f" LIMIT {limit}"
    with engine.connect() as conn:
        return conn.execute(text(sql)).fetchall()


def make_results(genes, level):
    """Pretend the predictor returned `level` for every gene."""
    return [
        GeneExpressionResult(
            gene_id=lt,
            relative_expression=level,
            confidence=1.0,
            prediction_source="sensitivity-test",
            reference_expression_tpm=tpm,
        )
        for lt, tpm in genes
    ]


def growth_of(result):
    for attr in ("growth_rate", "objective_value", "growth"):
        val = getattr(result, attr, None)
        if val is not None:
            return val
    if isinstance(result, dict):
        return result.get("growth_rate", 0.0)
    return 0.0


# ------------------------------------------------------------------ #
section("1. TF RESOLVER — do the environment rules actually fire?")
# ------------------------------------------------------------------ #

async def check_tfs():
    r = TFResolver()

    async def resolve(**kw):
        env = dict(temperature=37.0, ph=7.0, oxygen_level="aerobic",
                   carbon_source="glucose", nitrogen_source="ammonium")
        env.update(kw)
        states = await r.resolve(**env)
        return {name: s.is_active for name, s in states.items()}

    glucose = await resolve()
    lactose = await resolve(carbon_source="lactose")
    anaerobic = await resolve(oxygen_level="anaerobic")
    hot = await resolve(temperature=45.0)

    for label, passed in [
        ("CRP off on glucose", glucose.get("CRP") is False),
        ("CRP on with lactose", lactose.get("CRP") is True),
        ("FNR on anaerobically", anaerobic.get("FNR") is True),
        ("FNR off aerobically", glucose.get("FNR") is False),
        ("RpoH on at 45C", hot.get("RpoH") is True),
    ]:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")

    active = sum(1 for v in glucose.values() if v)
    print(f"\n  TFs resolved: {len(glucose)} | active on glucose: {active}")
    if active > len(glucose) * 0.8:
        print("  NOTE: most TFs default to active — only 18 have real rules.")


try:
    asyncio.run(check_tfs())
except Exception:
    print(traceback.format_exc()[-600:])

# ------------------------------------------------------------------ #
section("2. HOW MANY REACTIONS CAN EXPRESSION EVEN TOUCH?")
# ------------------------------------------------------------------ #

genes = load_genes()
compiler = BoundCompiler()

print(f"  genes with reference TPM : {len(genes):,}")

bounds_baseline = []
try:
    bounds_baseline = compiler.compile(
        make_results(genes, 1.0), temperature=37.0, ph=7.0
    )
    print(f"  bounds produced          : {len(bounds_baseline):,}")
    print(f"  total reactions in model : 2,712")
    print(f"  coverage                 : {len(bounds_baseline)/2712:.1%}")
    if len(bounds_baseline) < 100:
        print("\n  Every other reaction keeps its iML1515 default bound,")
        print("  so expression cannot influence it at all.")
except Exception:
    print(traceback.format_exc()[-600:])

# ------------------------------------------------------------------ #
section("3. THE SENSITIVITY TEST")
# ------------------------------------------------------------------ #

solver = FBASolver()

print("\n  Same expression level for every gene, then solve.")
print("  If the AI layer matters, growth should fall as expression falls.\n")
print(f"  {'expression':>12}  {'bounds':>7}  {'growth':>10}  {'vs baseline':>12}")
print("  " + "-" * 50)

growths = {}
levels = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0)

for level in levels:
    try:
        b = compiler.compile(make_results(genes, level), temperature=37.0, ph=7.0)
        g = growth_of(solver.solve(b))
        growths[level] = g
        print(f"  {level:>12.3f}  {len(b):>7}  {g:>10.4f}")
    except Exception:
        print(f"  {level:>12.3f}  ERROR")
        print(traceback.format_exc()[-400:])
        break

baseline = growths.get(1.0)
if baseline:
    print()
    for level in levels:
        if level in growths:
            print(f"  {level:>12.3f}  ->  {growths[level]/baseline:>6.3f}x baseline")

# ------------------------------------------------------------------ #
section("4. VERDICT")
# ------------------------------------------------------------------ #

if len(growths) >= 2:
    spread = max(growths.values()) - min(growths.values())
    print(f"\n  Growth range across a 100,000x expression change: {spread:.6f}")

    if spread < 1e-4:
        print("""
  RESULT: expression has NO effect on the outcome.

  Everything the AI layer predicts is discarded before it reaches the
  answer. A perfectly trained model would produce these same numbers.
  Fixing the coupling matters more than training a model.""")
    elif spread < 0.05:
        print(f"""
  RESULT: expression has a WEAK effect ({spread:.4f} growth units).

  The signal reaches the answer but barely moves it. A trained model
  would make a small difference. Worth widening the coupling first.""")
    else:
        print(f"""
  RESULT: expression clearly drives the outcome ({spread:.4f} growth units).

  The pipeline is sensitive to what the AI layer predicts. Training a
  real model will change the answers meaningfully.""")

    up, base = growths.get(10.0), growths.get(1.0)
    if up is not None and base:
        if up <= base + 1e-9:
            print("""
  ALSO: 10x upregulation did not raise growth above baseline.
  The bound compiler only tightens bounds, never loosens them, so the
  model can predict a gene is OFF but never that it is BOOSTED.""")
        else:
            print(f"\n  10x upregulation raised growth to {up/base:.3f}x baseline.")
else:
    print("\n  Not enough successful runs to judge.")