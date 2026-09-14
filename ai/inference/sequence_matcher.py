"""Sequence matcher — the front door of Track A.

Owned by: Keshav

Given a gene ID and a DNA sequence, work out whether we are looking at a
gene we already know about. If we do, Track A can answer from the database
instead of guessing with a model.

Three possible outcomes:

    KNOWN_WILDTYPE  the ID is in our database and the coding sequence is
                    unchanged. Highest confidence — pure lookup.

    KNOWN_VARIANT   the ID is in our database but the sequence has been
                    edited. We know which gene it is, but not how the edit
                    changes its behaviour. Track B's job.

    NOVEL           we have never seen this. Track B entirely.

Note on sequence format
-----------------------
The contract specifies each input as [300bp upstream + CDS]. Our genes
table stores the CDS only, so we compare the CDS portion. We cannot yet
tell whether the upstream promoter region is wild-type, because the full
genome sequence is not stored in the database — only per-gene CDS.
That is a known gap, tracked in `upstream_comparable`.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

UPSTREAM_BP = 300          # per the contract
VALID_BASES = set("ACGTN")


class MatchType(str, Enum):
    KNOWN_WILDTYPE = "known_wildtype"
    KNOWN_VARIANT = "known_variant"
    NOVEL = "novel"


@dataclass
class GeneRecord:
    """One row from the genes table, held in memory."""
    locus_tag: str
    name: str | None
    product: str | None
    cds: str
    length_bp: int


@dataclass
class MatchResult:
    """What the matcher concluded about one input gene."""
    query_id: str
    match_type: MatchType
    locus_tag: str | None = None
    name: str | None = None
    product: str | None = None
    matched_by: str | None = None       # "gene_id" | "sequence" | None
    cds_identity: float | None = None   # 1.0 = identical, None = no comparison
    upstream: str | None = None         # the 300bp promoter region, if present
    upstream_comparable: bool = False   # can we check it against wild-type?
    notes: list[str] | None = None

    @property
    def is_known(self) -> bool:
        return self.match_type is not MatchType.NOVEL


def split_sequence(sequence: str) -> tuple[str, str]:
    """Split [300bp upstream + CDS] into its two parts.

    If the sequence is too short to contain an upstream region, the whole
    thing is treated as CDS and the upstream comes back empty.
    """
    seq = sequence.upper().strip()
    if len(seq) <= UPSTREAM_BP:
        return "", seq
    return seq[:UPSTREAM_BP], seq[UPSTREAM_BP:]


def sequence_identity(a: str, b: str) -> float:
    """Fraction of positions that agree, between 0.0 and 1.0.

    Same-length sequences are compared position by position, which is the
    common case for point mutations. Different lengths fall back to a
    cheap length-ratio estimate — good enough to distinguish "small edit"
    from "completely different", which is all we need here.
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    if len(a) == len(b):
        same = sum(1 for x, y in zip(a, b) if x == y)
        return same / len(a)

    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    if shorter in longer:
        return len(shorter) / len(longer)

    same = sum(1 for x, y in zip(shorter, longer) if x == y)
    return same / len(longer)


class SequenceMatcher:
    """Identifies input sequences against the known E. coli gene set.

    Loads the genes table once and keeps it in memory — roughly 5MB for
    4,651 genes, which is nothing, and it makes every lookup instant.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql://biosandbox:biosandbox@localhost:5432/biosandbox",
        )
        self._by_locus_tag: dict[str, GeneRecord] = {}
        self._by_name: dict[str, GeneRecord] = {}
        self._by_cds: dict[str, GeneRecord] = {}
        self._loaded = False

    # ---------------------------------------------------------------- #
    # Loading
    # ---------------------------------------------------------------- #

    def load(self) -> int:
        """Pull every gene into memory. Returns how many were loaded."""
        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT locus_tag, name, product, dna_sequence, length_bp "
                    "FROM genes WHERE dna_sequence IS NOT NULL"
                )
            ).fetchall()

        for locus_tag, name, product, cds, length_bp in rows:
            record = GeneRecord(
                locus_tag=locus_tag,
                name=name,
                product=product,
                cds=cds.upper(),
                length_bp=length_bp or len(cds),
            )
            self._by_locus_tag[locus_tag.lower()] = record
            self._by_cds[record.cds] = record
            if name:
                self._by_name[name.lower()] = record

        self._loaded = True
        return len(rows)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def gene_count(self) -> int:
        return len(self._by_locus_tag)

    # ---------------------------------------------------------------- #
    # Matching
    # ---------------------------------------------------------------- #

    def _lookup_id(self, gene_id: str) -> GeneRecord | None:
        key = gene_id.lower().strip()
        return self._by_locus_tag.get(key) or self._by_name.get(key)

    def match(self, gene_id: str, sequence: str) -> MatchResult:
        """Identify one gene. See module docstring for the three outcomes."""
        if not self._loaded:
            raise RuntimeError("SequenceMatcher.load() must be called first")

        notes: list[str] = []
        upstream, cds = split_sequence(sequence)

        if not upstream:
            notes.append(
                f"sequence is {len(sequence)}bp — too short to contain the "
                f"{UPSTREAM_BP}bp upstream region the contract requires"
            )

        bad = set(cds) - VALID_BASES
        if bad:
            notes.append(f"non-DNA characters in CDS: {sorted(bad)}")

        # Fast path: the caller told us the gene ID, so trust it and verify.
        record = self._lookup_id(gene_id)
        matched_by = "gene_id" if record else None

        # Slow path: unknown ID, so try to recognise the sequence itself.
        if record is None and cds:
            record = self._by_cds.get(cds)
            if record:
                matched_by = "sequence"
                notes.append(
                    f"gene_id {gene_id!r} not recognised, but the CDS matches "
                    f"{record.locus_tag}"
                )

        if record is None:
            return MatchResult(
                query_id=gene_id,
                match_type=MatchType.NOVEL,
                upstream=upstream or None,
                notes=notes or None,
            )

        identity = sequence_identity(cds, record.cds) if cds else None

        if identity == 1.0:
            match_type = MatchType.KNOWN_WILDTYPE
        else:
            match_type = MatchType.KNOWN_VARIANT
            if identity is not None:
                notes.append(
                    f"CDS differs from wild-type {record.locus_tag} "
                    f"({identity:.3%} identity, {len(cds)}bp vs "
                    f"{len(record.cds)}bp)"
                )

        return MatchResult(
            query_id=gene_id,
            match_type=match_type,
            locus_tag=record.locus_tag,
            name=record.name,
            product=record.product,
            matched_by=matched_by,
            cds_identity=identity,
            upstream=upstream or None,
            upstream_comparable=False,   # genome sequence not in DB yet
            notes=notes or None,
        )

    def match_many(
        self, gene_ids: list[str], sequences: list[str]
    ) -> list[MatchResult]:
        """Match a whole construct at once."""
        if len(gene_ids) != len(sequences):
            raise ValueError("gene_ids and sequences must be the same length")
        return [self.match(g, s) for g, s in zip(gene_ids, sequences)]


# --------------------------------------------------------------------------
# Manual smoke test:  python ai/inference/sequence_matcher.py
# --------------------------------------------------------------------------

if __name__ == "__main__":
    matcher = SequenceMatcher()
    count = matcher.load()
    print(f"loaded {count} genes\n")

    # Pull lacZ straight from the database so we can build test cases.
    from sqlalchemy import create_engine, text

    engine = create_engine(matcher.database_url)
    with engine.connect() as conn:
        lacz_cds = conn.execute(
            text("SELECT dna_sequence FROM genes WHERE locus_tag = 'b0344'")
        ).scalar()

    fake_upstream = "A" * UPSTREAM_BP

    cases = [
        ("wild-type lacZ", "b0344", fake_upstream + lacz_cds),
        ("lacZ by gene name", "lacZ", fake_upstream + lacz_cds),
        ("lacZ with a point mutation", "b0344",
         fake_upstream + "T" + lacz_cds[1:]),
        ("unknown ID, known sequence", "my_custom_gene",
         fake_upstream + lacz_cds),
        ("completely novel", "synthetic_1", fake_upstream + "ACGT" * 200),
        ("too short", "b0344", "ATGACCATG"),
    ]

    for label, gene_id, seq in cases:
        r = matcher.match(gene_id, seq)
        identity = f"{r.cds_identity:.4f}" if r.cds_identity is not None else "—"
        print(f"{label}")
        print(f"  type={r.match_type.value}  matched_by={r.matched_by}")
        print(f"  gene={r.locus_tag or '—'} ({r.name or '—'})  identity={identity}")
        if r.notes:
            for n in r.notes:
                print(f"  note: {n}")
        print()