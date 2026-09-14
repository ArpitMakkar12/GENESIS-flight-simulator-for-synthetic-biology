"""HyenaDNA wrapper — turns DNA sequences into numbers.

Owned by: Keshav

WHAT THIS IS
------------
HyenaDNA is a small neural network (1.6M parameters, 16MB on disk) that
has been trained on large amounts of DNA. It has learned, without being
told, which patterns matter — promoter-like regions, binding sites,
coding versus non-coding structure.

This wrapper feeds it a sequence and gets back its "understanding":

    "ATGACCATG..."  ->  256 numbers for every single base

Those 256-dimensional vectors are the raw material for everything
downstream. The expression predictor does not look at letters; it looks
at these.

MODEL DETAILS (from config.json)
--------------------------------
    d_model      256      numbers per base
    n_layer      4
    max_seq_len  32,770   bases
    vocab_size   12       A C G T N plus special tokens

POOLING
-------
The predictor needs one fixed-size vector per gene, not one per base.
Since the contract defines each input as [300bp upstream + CDS], we pool
those two regions separately — the promoter region carries the signal
about transcription strength, the CDS mostly identifies the gene.

USAGE
-----
    python ai/models/hyenadna_wrapper.py        # smoke test + benchmark
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np  # noqa: E402

DEFAULT_MODEL_PATH = "data/models/hyenadna-32k"

UPSTREAM_BP = 300        # per the contract
MAX_SEQ_LEN = 32_770     # hard limit of this checkpoint
EMBED_DIM = 256          # d_model


@dataclass
class GeneEmbedding:
    """Pooled representation of one gene."""
    promoter: np.ndarray | None   # (256,) mean over the upstream region
    cds: np.ndarray | None        # (256,) mean over the coding sequence
    whole: np.ndarray             # (256,) mean over everything
    n_bases: int
    truncated: bool

    def concat(self) -> np.ndarray:
        """Single feature vector for the predictor: [promoter | cds | whole]."""
        parts = []
        for v in (self.promoter, self.cds, self.whole):
            parts.append(v if v is not None else np.zeros(EMBED_DIM, dtype=np.float32))
        return np.concatenate(parts)


class HyenaDNAWrapper:
    """Loads HyenaDNA and converts DNA into embeddings.

    The model is loaded once and reused. Loading takes a few seconds;
    after that each sequence is a forward pass.
    """

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, num_threads: int | None = None):
        self.model_path = Path(model_path)
        self.num_threads = num_threads
        self._model = None
        self._tokenizer = None

    # ---------------------------------------------------------------- #
    # Loading
    # ---------------------------------------------------------------- #

    def load(self) -> None:
        """Load model and tokenizer into memory."""
        import torch
        from transformers import AutoModel, AutoTokenizer

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"No model at {self.model_path.resolve()}.\n"
                "Download it with:\n"
                "  python -c \"from huggingface_hub import snapshot_download; "
                "snapshot_download('LongSafari/hyenadna-small-32k-seqlen-hf', "
                "local_dir='data/models/hyenadna-32k')\""
            )

        if self.num_threads:
            torch.set_num_threads(self.num_threads)

        path = str(self.model_path)

        # trust_remote_code is required: HyenaDNA ships its own architecture
        # code (modeling_hyena.py) rather than using a built-in transformers
        # class. We downloaded these files ourselves, so we know what they are.
        self._tokenizer = AutoTokenizer.from_pretrained(
            path, trust_remote_code=True
        )
        self._model = AutoModel.from_pretrained(
            path, trust_remote_code=True
        )
        self._model.eval()     # inference mode — disables dropout

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    # ---------------------------------------------------------------- #
    # Embedding
    # ---------------------------------------------------------------- #

    def embed_raw(self, sequence: str) -> np.ndarray:
        """Return the per-base embedding matrix, shape (n_tokens, 256)."""
        import torch

        if not self.is_loaded:
            raise RuntimeError("call load() first")

        seq = sequence.upper().strip()
        if not seq:
            raise ValueError("empty sequence")

        if len(seq) > MAX_SEQ_LEN:
            seq = seq[:MAX_SEQ_LEN]

        tokens = self._tokenizer(seq, return_tensors="pt")

        with torch.no_grad():          # no gradients needed for inference
            out = self._model(**tokens)

        hidden = out.last_hidden_state  # (1, n_tokens, 256)
        return hidden[0].numpy()

    def embed_gene(self, sequence: str) -> GeneEmbedding:
        """Embed one gene and pool it into fixed-size vectors.

        Expects [300bp upstream + CDS] per the contract. Shorter
        sequences still work; the promoter vector just comes back None.
        """
        seq = sequence.upper().strip()
        truncated = len(seq) > MAX_SEQ_LEN

        matrix = self.embed_raw(seq)

        # The tokenizer may add special tokens at either end. Trim to the
        # number of actual bases so our slicing lines up with the DNA.
        n_bases = min(len(seq), MAX_SEQ_LEN)
        if matrix.shape[0] > n_bases:
            matrix = matrix[:n_bases]

        whole = matrix.mean(axis=0)

        if matrix.shape[0] > UPSTREAM_BP:
            promoter = matrix[:UPSTREAM_BP].mean(axis=0)
            cds = matrix[UPSTREAM_BP:].mean(axis=0)
        else:
            promoter = None
            cds = whole

        return GeneEmbedding(
            promoter=promoter,
            cds=cds,
            whole=whole,
            n_bases=n_bases,
            truncated=truncated,
        )

    def embed_many(self, sequences: list[str]) -> list[GeneEmbedding]:
        return [self.embed_gene(s) for s in sequences]


# --------------------------------------------------------------------------
# Smoke test and benchmark
# --------------------------------------------------------------------------

def _random_dna(n: int, seed: int = 0) -> str:
    rng = np.random.default_rng(seed)
    return "".join(rng.choice(list("ACGT"), size=n))


def main() -> None:
    print("=" * 62)
    print("HyenaDNA wrapper — smoke test and CPU benchmark")
    print("=" * 62)

    wrapper = HyenaDNAWrapper()

    print("\n[1] Loading model...")
    t0 = time.perf_counter()
    wrapper.load()
    print(f"    loaded in {time.perf_counter() - t0:.2f}s")

    print("\n[2] Embedding a short sequence")
    matrix = wrapper.embed_raw("ATGACCATGATTACGGATTCACTG")
    print(f"    input  : 24 bases")
    print(f"    output : {matrix.shape}  (tokens x dimensions)")
    print(f"    first 5 numbers for base 1: {matrix[0][:5].round(3)}")

    print("\n[3] Pooling a realistic gene (300bp promoter + 1000bp CDS)")
    gene = _random_dna(1300)
    emb = wrapper.embed_gene(gene)
    print(f"    promoter vector : {emb.promoter.shape}")
    print(f"    cds vector      : {emb.cds.shape}")
    print(f"    combined        : {emb.concat().shape}   <- feeds the predictor")

    print("\n[4] CPU benchmark")
    print(f"    {'length':>8}  {'time':>9}  {'per 1kb':>9}")
    print(f"    {'-'*8}  {'-'*9}  {'-'*9}")

    timings = {}
    for length in (500, 1_300, 3_400, 10_000):
        seq = _random_dna(length, seed=length)
        wrapper.embed_gene(seq)                      # warm up
        t0 = time.perf_counter()
        runs = 3
        for _ in range(runs):
            wrapper.embed_gene(seq)
        elapsed = (time.perf_counter() - t0) / runs
        timings[length] = elapsed
        print(f"    {length:>8}  {elapsed:>8.3f}s  {elapsed/(length/1000):>8.3f}s")

    print("\n[5] Does this fit the budget?")
    per_gene = timings[1_300]
    print(f"    typical gene (1.3kb) : {per_gene:.3f}s")
    for n in (1, 5, 10, 20):
        total = per_gene * n
        verdict = "OK" if total < 2.0 else "OVER BUDGET"
        print(f"    {n:>2} gene construct     : {total:>6.3f}s   {verdict}")

    print("\n" + "=" * 62)
    print("Budget is <2s per construct. If a 10-gene construct is over,")
    print("options are: cache embeddings, batch the forward passes, or")
    print("export to ONNX (usually 2-3x faster than PyTorch on CPU).")
    print("=" * 62)


if __name__ == "__main__":
    main()