# GENESIS — The AI Layer, End to End

**Author:** Keshav Sharma
**Date:** 2 October 2026
**Scope:** everything under `ai/`, plus `backend/app/services/rbs_calculator.py`
and `backend/app/data/build_training_data.py`
**Total:** ~4,900 lines across 17 files

Every number in this document was measured, not estimated. §8 says how to
reproduce each one.

---

## 1. What the system does, in one paragraph

You paste a piece of DNA and describe the conditions the cell is growing in —
temperature, pH, oxygen, what it is being fed. The system tells you **whether
the organism survives and how fast it grows**, and shows the reasoning in
between: which genes it recognised, how strongly each is expressed, which
regulators that environment switches on, and which metabolic reactions end up
constrained as a result.

It is a flight simulator for a cell. Not a design tool that invents DNA — a
test bench that tells you what a given piece of DNA would do.

```
     INPUT                          OUTPUT
┌──────────────────┐         ┌──────────────────────┐
│ DNA sequence     │         │ viable? yes / no     │
│ 42 °C            │   ──>   │ growth rate /hr      │
│ anaerobic        │         │ per-gene expression  │
│ glucose          │         │ which TFs fired      │
└──────────────────┘         └──────────────────────┘
```

---

## 2. The four layers, and why there are four

This is the design decision everything rests on.

A naive version would be: feed the DNA to a neural network, get expression out.
That fails for three separate reasons, and each one created a layer.

### Layer 1 — Identify. *"Which gene am I even looking at?"*

**Why:** we already hold measured expression for 4,351 real *E. coli* genes. If
someone pastes *lacZ*, guessing with a model when the lab measurement is sitting
in the database would be strictly worse. So the first question is never "how
strong is this?" but "do I already know this?"

Three answers: **known and unchanged**, **known but edited**, **never seen it**.
Sensitive enough to spot one changed base out of 3,075.

### Layer 2 — Baseline. *"How strongly is it normally expressed?"*

**Why:** known genes get their measured value. Only genuinely novel sequences go
through the neural network. This is why the system is accurate in practice even
though the model alone is modest — most real input is a lookup, not a prediction.

### Layer 3 — Environment. *"What does this condition change?"*

**Why — the key insight:** the sequence model is blind to environment. The same
DNA at 37 °C and 42 °C produces an *identical* vector, because nothing about
temperature is written in the letters. A model can never learn environment
response from sequence alone.

Real cells respond through **transcription factors** — proteins that sit on DNA
and switch genes on or off. So environment sensitivity is not machine learning
at all. It is a lookup in 10,790 regulator→gene edges:

```
42 °C      ->  RpoH switches ON   ->  177 heat-shock genes respond
no oxygen  ->  FNR switches ON    ->  323 anaerobic genes respond
lactose    ->  CRP + LacI flip    ->  556 catabolic genes respond
```

### Layer 4 — Translation. *"Will the ribosome actually start here?"*

**Why:** the promoter decides how many mRNA *copies* exist. The ribosome binding
site decides how much *protein* comes off each copy. Two genes with identical
promoters and different RBSs differ a hundredfold in output. This layer is pure
physics — thermodynamics, no training data.

```
[promoter] ....... [RBS] [ATG] [coding sequence]
     │                │
  how much mRNA    how much protein
  (layers 1-3)      (layer 4)
```

---

## 3. Every file, what it does, and how it reaches the output

### The live prediction path — runs on every simulation

| File | Lines | What it does | How it reaches the output |
|---|---|---|---|
| `ai/inference/predictor.py` | 557 | **The entry point.** Implements the `ExpressionPredictor` contract the backend calls. Runs all four layers per gene. | Everything funnels through here. Its `relative_expression` becomes the flux bound on every reaction that gene catalyses. |
| `ai/inference/sequence_matcher.py` | 294 | Layer 1. Loads 4,651 genes; decides known-unchanged / known-edited / novel. | Decides **lookup vs model** — whether an answer is measured (0.85) or guessed (0.35). |
| `ai/inference/env_conditioner.py` | 182 | Layer 3's foundation. Defines which regulators are ON under *reference* conditions; turns 5 environment settings into 19 numbers. | Without a defined reference state, "2× expression" has no meaning. This file is what the word *relative* refers to. |
| `ai/models/model_registry.py` | 315 | Loads and caches models, reports versions. Deliberately does **not** load HyenaDNA unless a novel sequence appears. | Why a known-gene simulation costs 34 ms rather than 15–30 s. |
| `ai/models/expression_fusion.py` | 437 | The trained model as a class. PCA → 100 dims + 29 hand features → ridge and gradient boosting, averaged. | Only used for novel DNA, where no measurement exists. |
| `ai/models/hyenadna_wrapper.py` | 255 | Wraps HyenaDNA (1.6 M params). Turns DNA letters into 768 numbers. | The feature extractor the model above consumes. |
| `backend/app/services/rbs_calculator.py` | 597 | Layer 4. Thermodynamic translation initiation rate via ViennaRNA. No training data — physics. | Fills `rbs_score` on every result. Protein yield per mRNA. |

### The training path — run once, offline

| File | Lines | What it does | How it reaches the output |
|---|---|---|---|
| `ai/training/inspect_precise.py` | 185 | Validates PRECISE-1K (published RNA-seq) against our genes table. | **This file unblocked the project.** We had 11 labelled promoters; this found 4,331. |
| `backend/app/data/build_training_data.py` | 202 | Extracts 300 bp upstream of every gene. Self-validating: re-extracts each CDS and compares against the stored one. | Produces the training set. 4,331 / 4,351 = **99.5%** verified. |
| `ai/training/encode_promoters.py` | 189 | Runs all 4,330 promoters through HyenaDNA → a 4330 × 768 matrix. 102 s. | The input to training. |
| `ai/training/train_expression_v2.py` | 271 | **The model that shipped.** Held-out r = 0.378. | Produces `expression_model_v2.joblib`, which the registry loads. |
| `ai/training/train_expression.py` | 213 | v1, kept for comparison (r = 0.291). | Evidence the v2 design choices were worth making. |
| `ai/training/train_operon_aware.py` | 353 | Tests whether operon leaders are more predictable than internal genes. | A scientific finding, not a shipped model. See §6. |
| `ai/training/export_onnx.py` | 315 | Exports to ONNX **and numerically verifies** against the original. | Deployment path. Partial — see §6. |

### Verification — how we know any of it is true

| File | Lines | What it proves |
|---|---|---|
| `backend/verify_pipeline.py` | 203 | That expression **actually drives** the simulation. Sweeps expression 0.001 → 100 and watches growth move. |
| `tests/test_presets.py` | 186 | End to end: do the 5 presets give different answers, inside budget? |
| `contracts/interfaces.py` | 96 | **Shared with Arpit.** The agreed data shapes. Changing it needs both of us. |

---

## 4. A complete worked example

One real request, traced all the way through. This is the actual measured output
of `python ai/inference/predictor.py`, not an illustration.

**Input:** five known genes, grown on **lactose** instead of glucose.

### Step 0 — what arrives

```python
PredictionInput(
    gene_ids       = ["b0344",  # lacZ  - digests lactose
                      "b0002",  # thrA  - amino acid synthesis
                      "b0014",  # dnaK  - heat-shock chaperone
                      "b4143",  # groL  - heat-shock chaperone
                      "b0720"], # gltA  - citrate synthase, TCA cycle
    gene_sequences = [ "TTGACAATT...AAAGAGGAGAAA" + "ATGAAACGC..." ],
                     #  └─ 300bp upstream ─┘ └─ RBS ─┘   └─ CDS ─┘
    tf_activation  = {"CRP": True,    # no glucose -> CRP active
                      "LacI": False,  # lactose present -> LacI lets go
                      "FNR": False, "ArcA": False, "RpoH": False, ...},
    temperature    = 37.0,
    oxygen         = "aerobic",
    carbon_source  = "lactose",
)
```

### Step 1 — identify (Layer 1)

`SequenceMatcher` finds all five locus tags, then compares the submitted DNA
against the stored coding sequence.

```
verdict:    KNOWN_VARIANT      (the ID is ours, the sequence is not)
confidence: 0.50
```

> **Read that carefully — it is doing the right thing.** We deliberately fed a
> synthetic promoter, so the matcher correctly reports "this is lacZ, but
> somebody edited it" and drops confidence from 0.85 to 0.50. Feeding the real
> genomic sequence, or no sequence at all, returns `KNOWN_WILDTYPE` at 0.85.
> **The confidence number is reporting on our test input, not on a weakness.**

### Step 2 — baseline (Layer 2)

Known genes skip the neural network entirely and read the measured PRECISE-1K
value:

```
b0344 lacZ      3.0 TPM          <- note how low
b0002 thrA  1,273.5 TPM
b0014 dnaK    760.4 TPM
b4143 groL  1,154.4 TPM
b0720 gltA  2,157.1 TPM
```

> **Why lacZ is almost silent:** reference conditions are glucose, and on
> glucose LacI is actively repressing the lac operon. A cell does not build the
> lactose machinery it has no use for. **3.0 TPM is the biology being correct**,
> and it is exactly why this gene is the right one to test lactose with.

The model's r = 0.378 never enters this path. **HyenaDNA is not even loaded**
(`hyenadna: False (lazy on purpose)`).

### Step 3 — environment (Layer 3)

Compare the submitted TF state against the reference state. Two flips:

| Regulator | Reference | Now | Meaning |
|---|---|---|---|
| LacI | ON (repressing) | OFF | released — transcription can start |
| CRP | OFF | ON | activated — recruits polymerase to catabolic genes |

Then for each gene, look up which of those two regulate it, and in which
direction:

| Gene | Regulators that fired | Net log₂ | Fold |
|---|---|---|---|
| b0344 lacZ | `LacI-` released (repressor off) | +1.0 | **2.00×** |
| b0720 gltA | `Crp+` activated | +1.0 | **2.00×** |
| b0002, b0014, b4143 | none — not lactose-regulated | 0 | 1.00× |

Effects sum in log space, then are damped by √n, because biological effects are
**sub-additive** — two activators do not literally double twice. Capped at 16×
either way so a heavily regulated gene cannot produce nonsense.

> **`gltA` rising is the interesting one.** It is not an obvious lactose gene;
> it sits in the TCA cycle. It moves because CRP genuinely activates it when
> glucose runs out — the cell switches to burning other carbon properly. **That
> edge was dead until today** (see §7).

### Step 4 — translation (Layer 4)

The RBS calculator reads the 20 bases before the start codon, finds the
Shine–Dalgarno motif, and computes how favourably the ribosome binds:

```
SD motif found:  AGAGGAGA, 2 bases before ATG
dG_binding    = -6.60 kcal/mol      (what binding gains)
dG_total      = -3.29 kcal/mol      (negative = favourable)
rate          = 11,008              (arbitrary units; ratios are what count)
rbs_score     = 0.5774              (log-compressed to 0-1)
```

All five genes share the same test RBS, so all five score 0.5774 — correct,
since they were given identical upstream DNA.

### Step 5 — what comes back

```python
GeneExpressionResult(
    gene_id                  = "b0344",
    relative_expression      = 2.00,       # 2x more than at reference
    confidence               = 0.50,       # known gene, edited sequence
    prediction_source        = "lookup",   # Track A, measured
    rbs_score                = 0.5774,
    reference_expression_tpm = 3.0,        # the absolute anchor
)
```

### Step 6 — how that becomes a growth rate (Arpit's half)

```
enzyme amount  ∝  relative_expression × reference_expression_tpm
                     │
                     ▼
         bound_compiler.py sets the maximum flux
         through every reaction this gene catalyses
                     │
                     ▼
         COBRApy solves 2,712 reactions simultaneously
         for the fastest growth the constraints allow
                     │
                     ▼
              growth rate, per hour
```

### Measured timings

```
first call   162 ms     includes loading 4,351 genes + 3,394 regulator sets
subsequent    34 ms     for 5 genes, RBS scoring included
budget     2,000 ms
```

34 ms against a 2,000 ms budget — **59× headroom.** Fast because known genes
never touch the neural network.

---

## 5. What the system can do today — with the evidence

| Capability | Evidence |
|---|---|
| Recognise any of 4,651 *E. coli* genes from raw DNA | `sequence_matcher.py`; detects a 1-base change in 3,075 |
| Tell a wild-type gene from an edited one | three-way verdict, confidence 0.85 / 0.50 / 0.35 |
| Give measured expression for known genes | 4,351 genes anchored to PRECISE-1K RNA-seq |
| Predict expression for DNA nobody has measured | HyenaDNA + ensemble, held-out r = 0.378 on 866 unseen genes |
| **Respond correctly to the environment** | 3,394 genes carry regulator sets; verified table below |
| Score ribosome binding from physics alone | B0034 / B0033 = **177×** against a published 100–300× |
| Drive the actual simulation | `verify_pipeline.py`: growth spans 0.0 → 0.877 across a 100,000× expression range; 2,229 of 2,712 reactions get expression-derived bounds |
| Run inside the latency budget | 34 ms for 5 genes; worst case 262 ms at the 50-gene RBS cap |
| Say how much to trust each answer | every result carries `confidence` + `prediction_source` |

### Verified biology — the table to show in the review

Measured output across the four presets. Each row is a prediction; the last
column is whether biology agrees.

| Condition | Gene | Predicted | Biologically correct? |
|---|---|---|---|
| Reference (37 °C, glucose, O₂) | all five | 1.00× | yes — nothing changed, so nothing moves |
| 42 °C heat shock | b0014 dnaK | **2.00×** | yes — chaperone, refolds heat-damaged protein |
| 42 °C heat shock | b4143 groL | **2.00×** | yes — chaperone |
| 42 °C heat shock | b0344, b0002, b0720 | 1.00× | yes — not heat-shock genes, correctly unmoved |
| Anaerobic | b0720 gltA | **0.50×** | yes — ArcA represses the TCA cycle without oxygen |
| Lactose | b0344 lacZ | **2.00×** | yes — the enzyme that digests lactose |
| Lactose | b0720 gltA | **2.00×** | yes — CRP activates it when glucose is gone |

**The point to make:** each preset moves exactly the genes it biologically
should, and leaves the rest at 1.00×. A system that moved everything, or nothing,
would be far easier to build and worth nothing.

---

## 6. What is honest about the limitations

Being straight about these is stronger than overclaiming, and a reviewer will
find them anyway.

**The trained model is weak: r = 0.378, R² ≈ 0.14.** It explains about 14% of
the variance. Two things make that defensible:

1. **HyenaDNA earns its place.** Embeddings alone score 0.345; hand-crafted
   promoter features alone score 0.223. The foundation model contributes real
   signal, not decoration.
2. **The model extracts nearly everything available.** Prediction spread matches
   √R² in every run — the mathematically optimal value for that level of
   predictive power. Doing better needs **more context than 300 bp**, not a
   better model.

Supporting that: operon leaders predict at r = 0.363, genes buried inside an
operon at 0.297. About 37% of *E. coli* genes have no promoter in their own
300 bp at all — they are transcribed from a shared upstream promoter. The
information is not in the window.

**And it barely matters in practice,** because the model only handles sequences
nobody has measured. Everything else is a lookup — all five genes above came
back `source=lookup`.

**Fold-changes are directionally right, not quantitatively calibrated.** Every
regulator contributes the same ±1.0 in log₂, i.e. a flat 2× per regulator,
because we have one global constant rather than per-edge strengths. Real lac
induction is closer to 100–1000×, not 2×. **We predict which genes move and in
which direction, confidently; we do not predict by how much.** Per-edge
strengths would need fitting against condition-specific RNA-seq, which is the
obvious next piece of work.

**ONNX export is partial.** Ridge exports and verifies (3.81e-06, 2.1× faster);
HyenaDNA exports and verifies (6.18e-04); gradient boosting does not export at
all — `skl2onnx` cannot handle `HistGradientBoostingRegressor`. Since the
predictor is a 50/50 ridge + boosting blend, ONNX covers **the linear half plus
the encoder**, not the full model. Not blocking: PyTorch already meets budget.

**RBS absolute rates are context-dependent.** The same part scores differently
in different surrounding sequence — biologically true, mRNA structure really
does matter, but it means only *ratios* are meaningful, never the raw number.
Sequences with no detectable SD motif all floor at the same value, so the
calculator ranks confidently but cannot finely distinguish flavours of "dead".

**RBS scoring is capped at 50 genes per request.** Each one costs ~5 ms of
ViennaRNA folding, so 1,500 genes would take 7.9 s against a 2 s budget. Past
the cap `rbs_score` is `None` and the metadata says why. Results are cached, so
a repeated window is effectively free.

**Baseline growth is conservative.** At reference conditions the simulator gives
0.2883 while iML1515's own maximum is 0.877. A scaling constant in
`bound_compiler.py` is probably too tight. Arpit's file.

---

## 7. Three defects found in today's audit — and fixed

Worth presenting as process, not just outcome: the tests were passing before
this audit. They verified that expression *moves* growth, not that the *right
genes* move.

### 7.1 `rbs_score` was never computed

The contract declares it "computed by AI layer, not user-supplied". The
predictor hardcoded `rbs_score=None`, so 597 lines of validated RBS calculator
sat orphaned — nothing in the codebase called it. **Now wired**, with `None`
preserved honestly when there is no sequence to read rather than inventing a
number.

### 7.2 The RBS energy model double-counted mRNA unfolding

`dG_total` was computed as bare SD:anti-SD duplex energy, *minus* the mRNA
folding energy. But a duplex energy already assumes the motif is free and
unpaired, so subtracting the folding cost charges for the same unfolding twice.
Every sequence came out **positive** — meaning a ribosome binding even a known
strong RBS would be energetically uphill, which is false.

Replaced with a true net binding energy, `cofold(mRNA + 16S) − fold(mRNA)`, over
the ribosome's actual footprint (−20 to +13). `cofold` has to break existing
structure before it can pair, so the unfolding cost is already inside it.

| | before | after |
|---|---|---|
| B0034 / B0033 ratio | 847× | **177×** (published 100–300×) |
| dG, strong RBS | +2.41 — unfavourable | **−3.29** — favourable |
| B0033, a weak-but-real RBS | 0 — dead | **62** — weak |

### 7.3 Two master regulators never fired at all

`REFERENCE_TF_STATE` spells them `CRP` and `FNR`, the way the literature does.
The TRN, built from RegulonDB, spells them `Crp` and `Fnr`. Both seeders run —
`seed_regulondb.py` inserts curated edges, then `seed_precise.py` inserts TRN
names **verbatim** — so the database held them as *separate transcription
factors*, and matching case-sensitively reached neither.

Those are the two worst regulators to lose: **CRP is the master carbon-source
switch** and **FNR is the master oxygen switch**. The anaerobic preset had been
running on ArcA alone.

```
crp:  556 edges        <- unreachable before
fnr:  323 edges        <- unreachable before
arca: 236, rpoh: 177, laci: 3     <- these always worked
```

Fixed by matching case-insensitively, **plus dedup** — because matching
case-insensitively would otherwise count a gene carrying both spellings twice
and inflate the √n damping denominator.

**Result: environment-responsive genes go from 951 to 1,293.** The visible proof
is in §4 — `gltA` now rises 2× on lactose, where it previously sat at 1.00×.

---

## 8. What is NOT done — and it is not on my side

Two small things in Arpit's files currently stop the AI layer from reaching the
product. Both have exact fixes in `docs/PHASE4_HANDOFF.md` §6.

**1. The runner only asks about three hardcoded genes.**

```python
gene_ids = gene_ids or ["b0002", "b0344", "b3702"]
```

None of those three are regulated by FNR, ArcA, RpoH or RpoS, so when those
regulators fire nothing in the list responds and the UI shows identical
expression across presets. **The mechanism works; the pipeline is asking the
wrong question.** With ~1,500 genes it constrains most of the metabolic model
instead of 3 reactions out of 2,712.

Pass empty strings as the sequences — every one of those genes is known, so the
predictor resolves them by ID without reading DNA, and the 50-gene RBS cap keeps
it fast.

**2. `prediction_source` is dropped in serialisation.** The predictor sets it on
every result; the API reports `unknown`. Probably a missing field on the Pydantic
response schema.

---

## 9. How to verify any claim in this document

```bash
docker compose up -d db                       # the predictor needs the database

python ai/inference/predictor.py              # the 4 presets, all numbers in §4
python backend/app/services/rbs_calculator.py # B0034 vs B0033 ranking
python ai/models/model_registry.py            # what is loaded, from where
python tests/test_presets.py                  # end to end, needs the full stack
docker compose exec backend python verify_pipeline.py   # expression sensitivity
```

Each prints a pass/fail verdict rather than raw numbers to interpret.
