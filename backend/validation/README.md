# Validation

Two checks that compare GENESIS with published experiments. They answer the question every reviewer asks first: *does the simulator agree with real cells?*

| Check | Question | Ground truth | Tests |
| --- | --- | --- | --- |
| `essentiality` | Which single-gene deletions kill the cell? | ~300 essential genes in PRECISE-1K | The metabolic network and its gene rules |
| `growth_rates` | How fast does wild-type E. coli grow on each carbon source? | Measured growth rates in PRECISE-1K, each with its DOI | The full engine, exactly as the Simulate page runs it |

Both use [PRECISE-1K](https://github.com/SBRG/precise1k) (Lamoureux et al., *Nucleic Acids Research* 2023, [doi:10.1093/nar/gkad750](https://doi.org/10.1093/nar/gkad750)), from the same lab that built iML1515, pinned to one commit in `sources.py`.

## Run

From the project root, with the stack running (`docker compose up -d`):

```
docker compose exec backend python -m validation.essentiality
docker compose exec backend python -m validation.growth_rates
```

The first run downloads two small files (about 1.6 MB) into `validation/data/`, which is git-ignored. The essentiality check takes under a minute. The growth-rate check runs the full engine once per condition, so it takes a few seconds per condition.

Each check writes to `validation/results/`:

| File | What it holds |
| --- | --- |
| `essentiality_summary.md` | Scores, robustness tables, and every gene the model gets wrong |
| `essentiality_genes.csv` | One row per gene: knockout growth, model call, lab call |
| `growth_rates_summary.md` | Scores, per-condition table with sources, and which experiments were used |
| `growth_rates.csv` | One row per condition, measured and predicted |
| `growth_rates.svg` | The chart: measured vs predicted, one row per condition |

Commit the `results/` folder. The numbers are the project's evidence, and a reviewer should be able to read them without running anything.

## How each check stays honest
**The engine's inputs come from somewhere else.** Growth on each carbon source is capped by how fast the cell can take that source up. The app uses rates measured in a separate study (Gerosa et al. 2015, listed in `simulation_runner.py`), never tuned to match PRECISE-1K. Sources nobody has measured fall back to the same carbon supply as glucose, and the growth-rate report shows which is which.

**It tests the real engine, not a copy.** `engine.py` borrows the app's own `FBASolver` and `SimulationRunner`. Change the app, and the next run tests the change.

**Essentiality uses a rich medium on purpose.** The lab measured essentiality in rich broth (LB), where cells import amino acids and nucleotides, so the genes that make them are not essential. Screening on the app's glucose medium instead more than triples the false positives (121 against 36 in development testing on iJO1366) and drops the MCC from 0.60 to 0.44 — a medium mismatch, not a model error. The check adds LB's nutrients to the app's medium and documents the list.

**Setup choices are stress-tested.** The essentiality report re-scores at four lethality cut-offs and re-runs at three nutrient uptake rates. If a result held only at one setting, that setting would be suspect.

**Nothing is dropped silently.** The growth-rate report lists every filter rule and how many experiments it removed, from every sample in PRECISE-1K down to the ones GENESIS can represent.

**Limits are stated.** More than half of the lab's essential genes are not in the metabolic model at all — mostly genes for replication, translation and cell division — so no metabolic model can predict them either way. The report gives the exact count. PRECISE-1K has no anaerobic growth rates, and every usable experiment is at pH 7, so oxygen-free growth and the pH response are both untested here; the report lists the temperatures covered.

## Developing without Docker

Both checks accept `--model path/to/model.xml` to load a different SBML file, for example COBRApy's bundled iJO1366. Results from another model are **not** GENESIS results, and the scripts say so when they load one. The growth-rate check falls back to the iML1515-only prediction in that mode, because the full engine needs the database.