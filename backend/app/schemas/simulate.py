from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class SimulationRequest(BaseModel):
    construct_id: Optional[UUID] = None
    raw_sequence: Optional[str] = None
    temperature: float = Field(default=37.0, ge=20.0, le=50.0)
    ph: float = Field(default=7.0, ge=4.0, le=9.0)
    oxygen_level: str = Field(default="aerobic", pattern="^(aerobic|microaerobic|anaerobic)$")
    carbon_source: str = Field(default="glucose")
    nitrogen_source: str = Field(default="ammonium")


class GeneExpressionOut(BaseModel):
    gene_id: str
    gene_name: Optional[str] = None
    relative_expression: float
    confidence: float


class ReactionFluxOut(BaseModel):
    reaction_id: str
    reaction_name: Optional[str] = None
    flux_value: float
    flux_min: Optional[float] = None
    flux_max: Optional[float] = None


class SimulationResponse(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}

    task_id: UUID
    status: str
    growth_rate: Optional[float] = None
    doubling_time: Optional[float] = None
    viability_score: Optional[float] = None
    atp_balance: Optional[float] = None
    expression_predictions: Optional[list[GeneExpressionOut]] = None
    flux_distribution: Optional[list[ReactionFluxOut]] = None
    active_pathways: Optional[list[str]] = None
    bottlenecks: Optional[list[str]] = None
    model_versions: Optional[dict] = None
    computed_at: Optional[datetime] = None
    compute_time_ms: Optional[int] = None

