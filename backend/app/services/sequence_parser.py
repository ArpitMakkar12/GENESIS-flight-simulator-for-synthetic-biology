"""Parses raw DNA constructs into structured gene components.

Uses ORF detection to identify coding sequences within a raw DNA input,
and extracts the upstream promoter region (300bp) as required by the
AI prediction contract.

Owned by: Arpit
"""

from dataclasses import dataclass, field
from Bio.Seq import Seq


@dataclass
class ParsedGene:
    gene_id: str
    start: int
    end: int
    strand: str
    sequence: str
    promoter_seq: str | None = None
    rbs_seq: str | None = None


@dataclass
class ParsedConstruct:
    full_sequence: str
    genes: list[ParsedGene]
    total_length: int
    gc_content: float
    warnings: list[str] = field(default_factory=list)


# Minimum ORF length in nucleotides (100 codons = 300 bp)
MIN_ORF_LENGTH = 300
# Upstream region required by AI contract
UPSTREAM_BP = 300

START_CODONS = {"ATG", "GTG", "TTG"}
STOP_CODONS = {"TAA", "TAG", "TGA"}


class SequenceParser:
    """Parses DNA constructs into genes, promoters, RBS, and terminators.

    Uses simple ORF detection on both strands to identify coding sequences.
    Each ORF gets a synthetic gene_id and its 300bp upstream promoter region
    is extracted for the AI prediction contract.
    """

    def parse(self, dna_sequence: str) -> ParsedConstruct:
        """Parse a raw DNA sequence into structured components."""
        seq = dna_sequence.upper().strip()
        warnings: list[str] = []

        if not self.validate_sequence(seq):
            warnings.append("Sequence contains non-DNA characters; they were stripped.")
            seq = "".join(c for c in seq if c in "ATCGN")

        if len(seq) < MIN_ORF_LENGTH:
            warnings.append(f"Sequence is only {len(seq)}bp, too short for ORF detection.")
            return ParsedConstruct(
                full_sequence=seq,
                genes=[],
                total_length=len(seq),
                gc_content=self.calculate_gc_content(seq),
                warnings=warnings,
            )

        # Find ORFs on both strands
        genes: list[ParsedGene] = []
        gene_counter = 0

        # Forward strand
        for start, end in self._find_orfs(seq):
            gene_counter += 1
            gene_id = f"orf_{gene_counter:03d}"
            orf_seq = seq[start:end]

            # Extract 300bp upstream promoter
            promoter_start = max(0, start - UPSTREAM_BP)
            promoter_seq = seq[promoter_start:start] if start > 0 else None

            # The contract requires 300bp upstream + CDS concatenated
            full_gene_seq = (promoter_seq or "") + orf_seq

            genes.append(ParsedGene(
                gene_id=gene_id,
                start=start,
                end=end,
                strand="+",
                sequence=full_gene_seq,
                promoter_seq=promoter_seq,
            ))

        # Reverse complement strand
        rev_seq = str(Seq(seq).reverse_complement())
        for start, end in self._find_orfs(rev_seq):
            gene_counter += 1
            gene_id = f"orf_{gene_counter:03d}"
            orf_seq = rev_seq[start:end]

            promoter_start = max(0, start - UPSTREAM_BP)
            promoter_seq = rev_seq[promoter_start:start] if start > 0 else None
            full_gene_seq = (promoter_seq or "") + orf_seq

            # Map coordinates back to forward strand
            fwd_end = len(seq) - start
            fwd_start = len(seq) - end

            genes.append(ParsedGene(
                gene_id=gene_id,
                start=fwd_start,
                end=fwd_end,
                strand="-",
                sequence=full_gene_seq,
                promoter_seq=promoter_seq,
            ))

        if not genes:
            warnings.append("No ORFs found (minimum 300bp with start/stop codons).")

        return ParsedConstruct(
            full_sequence=seq,
            genes=genes,
            total_length=len(seq),
            gc_content=self.calculate_gc_content(seq),
            warnings=warnings,
        )

    def _find_orfs(self, sequence: str) -> list[tuple[int, int]]:
        """Find all ORFs in a single strand above minimum length."""
        orfs: list[tuple[int, int]] = []
        seq_len = len(sequence)

        for frame in range(3):
            i = frame
            while i < seq_len - 2:
                codon = sequence[i:i + 3]
                if codon in START_CODONS:
                    # Scan forward for stop codon
                    for j in range(i + 3, seq_len - 2, 3):
                        stop = sequence[j:j + 3]
                        if stop in STOP_CODONS:
                            orf_len = j + 3 - i
                            if orf_len >= MIN_ORF_LENGTH:
                                orfs.append((i, j + 3))
                            i = j + 3  # skip past stop
                            break
                    else:
                        i += 3
                        continue
                    continue
                i += 3

        # Sort by length descending, remove overlaps
        orfs.sort(key=lambda x: x[1] - x[0], reverse=True)
        filtered: list[tuple[int, int]] = []
        used = set()
        for start, end in orfs:
            overlap = False
            for pos in range(start, end, 50):
                if pos in used:
                    overlap = True
                    break
            if not overlap:
                filtered.append((start, end))
                for pos in range(start, end):
                    used.add(pos)

        return sorted(filtered, key=lambda x: x[0])

    def validate_sequence(self, sequence: str) -> bool:
        """Validate that a sequence contains only valid DNA characters."""
        valid_chars = set("ATCGNatcgn")
        return all(c in valid_chars for c in sequence)

    def calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content of a DNA sequence."""
        seq_upper = sequence.upper()
        gc_count = seq_upper.count("G") + seq_upper.count("C")
        return gc_count / len(seq_upper) if seq_upper else 0.0
