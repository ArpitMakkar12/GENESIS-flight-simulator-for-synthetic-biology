from dataclasses import dataclass


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


class SequenceParser:
    """Parses DNA constructs into genes, promoters, RBS, and terminators.

    Uses Biopython for ORF finding and feature annotation.
    """

    def parse(self, dna_sequence: str) -> ParsedConstruct:
        """Parse a raw DNA sequence into structured components."""
        # TODO: Implement using Biopython
        raise NotImplementedError

    def validate_sequence(self, sequence: str) -> bool:
        """Validate that a sequence contains only valid DNA characters."""
        valid_chars = set("ATCGNatcgn")
        return all(c in valid_chars for c in sequence)

    def calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content of a DNA sequence."""
        seq_upper = sequence.upper()
        gc_count = seq_upper.count("G") + seq_upper.count("C")
        return gc_count / len(seq_upper) if seq_upper else 0.0
