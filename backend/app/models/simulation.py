import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Sequence, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, deferred

from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    construct_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("constructs.id"), nullable=True, index=True)

    # Human-friendly identity
    # run_number: #1, #2, #3 ... handed out by Postgres in creation order and
    # never reused, so "Run #12" always means the same simulation.
    # name: optional label the user types (e.g. "Heat shock test"). When empty,
    # the UI builds a title from the conditions instead.
    run_number: Mapped[int] = mapped_column(
        Integer,
        Sequence("simulations_run_number_seq"),
        server_default=text("nextval('simulations_run_number_seq')"),
        nullable=False,
        unique=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)

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
    expression_all: Mapped[dict | None] = deferred(mapped_column(JSONB, nullable=True))
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
        return f"<Simulation #{self.run_number} {self.id} status={self.status}>"