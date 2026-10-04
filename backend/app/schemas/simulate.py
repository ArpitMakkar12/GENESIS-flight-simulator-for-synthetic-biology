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
    prediction_source: Optional[str] = None     # "lookup", "model", or "fallback"
    rbs_score: Optional[float] = None           # thermodynamic RBS score (0-1)
    reference_tpm: Optional[float] = None       # absolute expression anchor (TPM)


class ReactionFluxOut(BaseModel):
    reaction_id: str
    reaction_name: Optional[str] = None
    flux_value: float
    flux_min: Optional[float] = None
    flux_max: Optional[float] = None


class SimulationResponse(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}

    task_id: UUID
    solver_status: Optional[str] = None          # FBA solver outcome: 'optimal', 'infeasible'
    growth_state: Optional[str] = None           # human-readable: 'optimal', 'slowed', 'stressed', 'not-viable'
    status: Optional[str] = None                 # kept for backwards compat (= solver_status)
    growth_rate: Optional[float] = None
    doubling_time: Optional[float] = None
    viability_score: Optional[float] = None
    atp_balance: Optional[float] = None
    expression_predictions: Optional[list[GeneExpressionOut]] = None
    expression_summary: Optional[dict] = None
    flux_distribution: Optional[dict] = None     # top 100 reactions: {rxn_id: flux_value}
    flux_summary: Optional[dict] = None
    active_pathways: Optional[list[str]] = None
    active_tfs: Optional[list[str]] = None
    regulator_state: Optional[dict] = None       # master regulator -> active?
    tf_state_changes: Optional[dict] = None      # regulators flipped vs reference
    infeasibility_reason: Optional[str] = None   # set only when growth fails
    bottlenecks: Optional[list[str]] = None
    model_versions: Optional[dict] = None
    conditions: Optional[dict] = None
    computed_at: Optional[datetime] = None
    compute_time_ms: Optional[int] = None

