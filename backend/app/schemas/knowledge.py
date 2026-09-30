from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class GeneResponse(BaseModel):
    id: UUID
    locus_tag: str
    name: Optional[str] = None
    product: Optional[str] = None
    start_pos: int
    end_pos: int
    strand: str
    gc_content: Optional[float] = None
    length_bp: Optional[int] = None

    class Config:
        from_attributes = True


class ReactionResponse(BaseModel):
    id: UUID
    bigg_id: str
    name: Optional[str] = None
    subsystem: Optional[str] = None
    reaction_formula: Optional[str] = None
    is_reversible: bool
    ec_number: Optional[str] = None

    class Config:
        from_attributes = True


class TFResponse(BaseModel):
    id: UUID
    name: str
    tf_family: Optional[str] = None
    sensing_signal: Optional[str] = None
    active_form: Optional[str] = None
    active_conditions: Optional[dict] = None
    regulated_gene_count: int = 0

    class Config:
        from_attributes = True


class RegulatedGeneResponse(BaseModel):
    gene_locus_tag: str
    gene_name: Optional[str] = None
    regulation_type: str
    confidence_score: Optional[float] = None

    class Config:
        from_attributes = True


class TFDetailResponse(BaseModel):
    id: UUID
    name: str
    tf_family: Optional[str] = None
    sensing_signal: Optional[str] = None
    active_form: Optional[str] = None
    active_conditions: Optional[dict] = None
    regulated_gene_count: int = 0
    regulated_genes: list[RegulatedGeneResponse] = []

    class Config:
        from_attributes = True


class PathwayResponse(BaseModel):
    subsystem: str
    reaction_count: int
    reactions: list[ReactionResponse]

