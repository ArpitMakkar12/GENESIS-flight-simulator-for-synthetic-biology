# GENESIS — Phase 4 Complete: AI Expression Engine

**From:** Keshav
**To:** Arpit
**Date:** 2 October 2026
**Branch:** `keshav/phase4-expression-engine`

---

## TL;DR

The AI layer is done. `predictor.py` returns real predictions, they respond
to the environment, and the whole thing runs in well under a millisecond for
known genes.

**Two things on your side are blocking the AI layer from showing up in the
product.** They are small, they are in your files, and they are in section 6.

---

## 1. What the AI layer does now

Three layers per gene, in order:

```
1. IDENTIFY   what gene is this?           SequenceMatcher
2. BASELINE   how strong is it normally?   database lookup, or the model
3. TF SHIFT   what changed vs reference?   regulatory network

relative_expression = adjusted / baseline
```

### Layer 1 — identification

`SequenceMatcher` loads all 4,651 genes and answers one of three ways:

| Verdict | Meaning | Confidence |
|---|---|---|
| `known_wildtype` | Our gene, sequence unchanged | 0.85 |
| `known_variant` | Our gene, someone edited it | 0.50 |
| `novel` | Never seen it | 0.35 |

Sensitive enough to catch a single changed base out of 3,075.

### Layer 2 — baseline

Known genes use their **measured** PRECISE-1K expression. That is real
experimental data and beats a model with held-out r = 0.378 every time. Only
genuinely novel sequences go through HyenaDNA and the trained model.

This is why the system is accurate in practice despite a modest model score —
most input is a lookup, not a prediction.

### Layer 3 — environment

The trained model reads sequence only. Same DNA at 37 °C and 42 °C gives the
same number — it has no idea what the temperature is.

Environment sensitivity is **not machine learning**. It is a lookup in the
10,783 regulator-gene interactions you seeded:

```
42 °C   ->  RpoH switches on  ->  every RpoH target rises
no O2   ->  FNR switches on   ->  every FNR target rises
lactose ->  LacI releases     ->  lac operon rises
```

Effects sum in log space, damped by sqrt(n) because biological effects are
sub-additive, capped at 16x so a heavily regulated gene cannot produce
nonsense.

---

## 2. Verified behaviour

Run `python ai/inference/predictor.py` to reproduce:

| Condition | Gene | Fold | Correct? |
|---|---|---|---|
| Heat shock 42 °C | b0014 (dnaK) | **2.0x** | yes, heat shock chaperone |
| Heat shock 42 °C | b4143 (groL) | **2.0x** | yes, heat shock chaperone |
| Lactose | b0344 (lacZ) | **2.0x** | yes, digests lactose |
| Lactose | b0720 (gltA) | **2.0x** | yes, CRP activates it off glucose |
| Anaerobic | b0720 (gltA) | **0.5x** | yes, ArcA represses the TCA cycle |
| Reference | all | 1.0x | yes, nothing changed |

Each preset moves exactly the genes it biologically should, and leaves the
rest at 1.0x.

**Speed: 34 ms for a 5-gene construct** (162 ms on the first call, which
loads 4,351 genes and 3,394 regulator sets). Budget was 2,000 ms — 59x
headroom. Known genes never touch the neural network, which is why.

> The earlier draft said 0.6 ms. That was measured before RBS scoring was
> wired in; ViennaRNA folding is what accounts for the difference. Still far
> inside budget, and capped so it cannot escape — see §4.

**One correction worth reading.** The `gltA` lactose row above is new. Until
today `REFERENCE_TF_STATE` spelled the regulators `CRP` and `FNR`, while the
TRN spells them `Crp` and `Fnr`, and both seeders insert into the same table —
so the database held them as *separate transcription factors* and
case-sensitive matching reached neither. **556 Crp edges and 323 Fnr edges
were dead**, which is the master carbon-source regulator and the master
oxygen regulator. The anaerobic preset had been running on ArcA alone.

Now matched case-insensitively, with dedup so a gene carrying both spellings
is not counted twice. **Environment-responsive genes: 951 → 1,293.**

---

## 3. The trained model, honestly

```
held-out Pearson r = 0.378  on 866 genes the model never saw
```

For context on how that was reached:

| Attempt | r |
|---|---|
| Baseline — always guess the average | ~0 |
| Ridge on embeddings only | 0.345 |
| Hand-built features only | 0.223 |
| Gradient boosting, first attempt | 0.291 |
| **PCA + hand features, ridge/boosting ensemble** | **0.378** |

**Two findings worth stating plainly.**

First, HyenaDNA earns its place: embeddings alone (0.345) clearly beat
hand-crafted promoter features alone (0.223). The foundation model is
contributing real signal, not decoration.

Second, the model is extracting close to everything available. Prediction
spread matches sqrt(R-squared) in every run — the mathematically optimal
value for that level of predictive power. Doing better needs more context
than 300bp, not a better model.

### Operon experiment

Genes that lead a transcription unit are more predictable than genes buried
inside one:

```
operon leaders   r = 0.363
operon internal  r = 0.297
```

That confirms the 300bp window carries real promoter signal — about 37% of
E. coli genes sit inside an operon and have no promoter in their own upstream
region at all. The effect was modest, so the all-genes model ships.

### What this means in practice

r = 0.378 explains about 14% of the variance. Real, but not accurate enough
to rely on alone. In the live system it only handles sequences nobody has
measured; everything else is a lookup.

---

## 4. RBS calculator

`backend/app/services/rbs_calculator.py` — thermodynamic translation
initiation rate, Salis 2009 method, using ViennaRNA for the folding terms.

Validated against three real iGEM parts whose relative strength is already
known, each embedded in 300bp of genuine upstream context — the same shape
the contract specifies, not the part in isolation:

```
BBa_B0034 (strong)   dG = -3.29   rate = 11,008
BBa_B0032 (medium)   dG = +0.61   rate =  1,903
BBa_B0033 (weak)     dG = +8.21   rate =     62
no SD motif at all   dG = +11.3   rate =     15
                                  -> B0034/B0033 = 177x
```

Published measurements put B0034 roughly two orders of magnitude above
B0033; 177x sits inside the reported 100-300x band. Reproduced from physics
alone, having never seen either part's measured strength.

**Corrected since the first draft of this document.** It previously reported
54,336 vs 316 (172x). Two things were wrong with that. The numbers were
measured on isolated parts rather than in sequence context, so they are not
what the pipeline reports. And the energy model double-counted: it took the
bare SD:anti-SD duplex energy and then separately subtracted the mRNA
folding energy, but a duplex energy already assumes the motif is unpaired,
so the unfolding cost was charged twice. Every dG_total came out positive,
meaning a ribosome binding a known-strong RBS would be energetically
uphill.

The binding term is now a true net energy, `cofold(mRNA + 16S) - fold(mRNA)`,
computed over the ribosome's own footprint (-20 to +13 around the start
codon). cofold has to break existing structure before it can pair, so the
unfolding cost is already inside that number and nothing is subtracted
afterwards. Strong RBSs now come out favourable, and weak-but-functional
ones read as weak rather than dead.

**`rbs_score` is now populated on every result.** It was hardcoded `None`
until today, so this module was orphaned — the contract declared the field
"computed by AI layer" and nothing computed it. Genes passed with an empty
sequence still return `None`, deliberately: there is no DNA to read, and an
honest gap beats a fabricated number.

Two performance notes, because each score costs ~5ms of ViennaRNA folding:

- Results are cached on the sequence window, so a repeat is effectively free.
- **Scoring is capped at 50 genes per request.** Past that, `rbs_score` is
  `None` for all of them and the metadata says why. 1,500 genes would
  otherwise take 7.9s against a 2s budget. This is why passing empty
  sequences for known genes (§6.1) matters — it skips this path entirely.

Degrades gracefully — if ViennaRNA is missing it falls back to the separable
approximation and **says so in every result**, so an approximate number is
never mistaken for a full calculation. The fallback preserves ranking but
its absolute scale differs from the vienna path.

---

## 5. ONNX export

`ai/training/export_onnx.py`

| Model | Result |
|---|---|
| Ridge | exported, verified at 3.81e-06, 2.1x faster |
| Gradient boosting | **failed** — skl2onnx cannot handle HistGradientBoostingRegressor |
| HyenaDNA | exported, verified at 6.18e-04 |

Be precise about what this gives us: the predictor is a 50/50 blend of ridge
and boosting, so ONNX covers the **linear half plus the encoder**, not the
full model. Useful, not yet a drop-in replacement.

Not blocking anything — PyTorch runs at 0.117 s/gene against a 2 s budget.

---

## 6. Two things I need from you

Both are in your files and both are small. Until they are done, **the AI
layer cannot affect the product**, however well it works in isolation.

### 6.1 The runner only asks about three genes

`backend/app/services/simulation_runner.py`:

```python
gene_ids = gene_ids or ["b0002", "b0344", "b3702"]
gene_sequences = gene_sequences or ["ATGC" * 200] * len(gene_ids)
```

None of those three are regulated by FNR, ArcA, RpoH or RpoS. So when those
regulators fire, nothing in the gene list responds — which is exactly what
`tests/test_presets.py` reports:

```
CHECK 2 — do the expression predictions differ?
  anaerobic: identical to reference
  heat_shock: identical to reference
```

The mechanism works. The pipeline just is not asking about the right genes.

Suggested fix:

```python
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL_SYNC)
with engine.connect() as conn:
    rows = conn.execute(text(
        "SELECT DISTINCT g.locus_tag FROM genes g "
        "JOIN enzyme_reactions er ON er.gene_id = g.id "
        "WHERE g.reference_expression_tpm IS NOT NULL"
    )).fetchall()

gene_ids = [r[0] for r in rows]
gene_sequences = [""] * len(gene_ids)   # all known -> lookup path
```

Empty sequences are deliberate. Every one of these genes is known, so the
predictor resolves them by ID and never reads the DNA. Passing ~1,500 full
sequences through the pipeline is what crashed the backend when I tried it.

Speed is not a concern — all lookup path, sub-millisecond.

**Why this matters:** the bound compiler can only constrain a reaction if it
has an expression value for the gene behind it. With 3 genes it constrains 3
reactions out of 2,712. With ~1,500 it constrains most of the model, and the
AI layer starts actually driving the simulation.

### 6.2 `prediction_source` is not reaching the API

The predictor sets it on every result (`lookup`, `model`, or `fallback`), but
it is dropped somewhere in serialisation. `test_presets.py` CHECK 4 shows:

```
reference  sources={'unknown': 3}
```

It should read `{'lookup': 3}`. Probably a missing field on the Pydantic
response schema in `backend/app/schemas/`.

This is the field that tells a user whether a number came from measured data
or a model guess — worth having in the UI.

---

## 7. Also worth knowing

**Baseline growth looks low.** At reference conditions the simulator gives
0.2883 while iML1515's own maximum is 0.877. Some scaling constant in
`bound_compiler.py` is probably conservative. Not blocking, your call.

**Model/migration drift happened three times** — `gene.py` and
`simulation.py` were changed without regenerating migrations, so fresh clones
failed on `seed_precise`. PR #14 fixed the third instance. Adding
`alembic check` to CI would catch it automatically.

**Startup should preload.** HyenaDNA takes 15 to 30 seconds to load. If that
happens during a user's first simulation it blows the latency budget. Call
this at server startup:

```python
predictor.load_models(include_hyenadna=True)
```

---

## 8. Files

### New / rewritten (mine)

```
ai/inference/predictor.py          real predictions, three-layer pipeline
ai/inference/env_conditioner.py    reference TF state + feature encoding
ai/inference/sequence_matcher.py   gene identification (now wired in)
ai/models/expression_fusion.py     the trained model as a proper class
ai/models/model_registry.py        model loading, caching, provenance
ai/models/hyenadna_wrapper.py      DNA encoder, benchmarked
ai/training/encode_promoters.py    4,331 promoters -> embeddings
ai/training/train_expression.py    v1
ai/training/train_expression_v2.py v2, the shipped model
ai/training/train_operon_aware.py  operon experiment
ai/training/export_onnx.py         ONNX export + verification
ai/training/inspect_precise.py     PRECISE-1K validation

backend/app/data/build_training_data.py   promoter extraction, 99.5% validated
backend/app/services/rbs_calculator.py    thermodynamic RBS scoring
backend/verify_pipeline.py                sensitivity test
tests/test_presets.py                     end-to-end preset verification
```

### Dependencies added to `ai/requirements.txt`

```
torch, transformers, einops          HyenaDNA
scikit-learn, joblib                 expression model
sqlalchemy, psycopg2-binary          read-only DB access
ViennaRNA                            RBS folding energies
skl2onnx, onnxruntime, onnxscript    ONNX export
requests                             PRECISE download
```

### Not in git (gitignored, correctly)

```
data/models/hyenadna-32k/           16MB
data/models/*.joblib                trained models
data/models/onnx/                   exported models
data/training/                      encoded arrays, CSV
data/precise/                       downloaded annotation files
```

Regenerate with:

```bash
python ai/training/inspect_precise.py
docker compose exec backend python -m app.data.build_training_data
python ai/training/encode_promoters.py
python ai/training/train_expression_v2.py
```

---

## 9. How to verify any of this

```bash
python ai/inference/predictor.py              # preset response, needs DB
python backend/app/services/rbs_calculator.py # B0034 vs B0033 ranking
python ai/models/model_registry.py            # what is loaded, from where
python tests/test_presets.py                  # end to end, needs the stack
docker compose exec backend python verify_pipeline.py   # expression sensitivity
```

Every one prints a pass/fail verdict rather than raw numbers to interpret.
