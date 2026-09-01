import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    construct_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constructs.id"), nullable=False, index=True)

    # Environmental parameters
    temperature: Mapped[float] = mapped_column(Float, default=37.0)
    ph: Mapped[float] = mapped_column(Float, default=7.0)
    oxygen_level: Mapped[str] = mapped_column(String(20), default="aerobic")
    carbon_source: Mapped[str] = mapped_column(String(50), default="glucose")
    nitrogen_source: Mapped[str] = mapped_column(String(50), default="ammonium")

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, running, completed, failed

    # Results (stored as JSONB for flexibility)
    expression_results: Mapped[dict | None] = mapped_column(JSONB)
    fba_results: Mapped[dict | None] = mapped_column(JSONB)
    flux_distribution: Mapped[dict | None] = mapped_column(JSONB)
    confidence_scores: Mapped[dict | None] = mapped_column(JSONB)
    model_versions: Mapped[dict | None] = mapped_column(JSONB)

    # Summary metrics
    growth_rate: Mapped[float | None] = mapped_column(Float)
    doubling_time: Mapped[float | None] = mapped_column(Float)
    viability_score: Mapped[float | None] = mapped_column(Float)
    atp_balance: Mapped[float | None] = mapped_column(Float)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    compute_time_ms: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    construct: Mapped["Construct"] = relationship(back_populates="simulations")

    def __repr__(self) -> str:
        return f"<Simulation {self.id} status={self.status}>"
