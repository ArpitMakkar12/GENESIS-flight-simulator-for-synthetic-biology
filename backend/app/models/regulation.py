import uuid
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TranscriptionFactor(Base):
    __tablename__ = "transcription_factors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    regulondb_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    tf_family: Mapped[str | None] = mapped_column(String(100))
    sensing_signal: Mapped[str | None] = mapped_column(String(200))
    active_form: Mapped[str | None] = mapped_column(String(50))
    active_conditions: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    regulations: Mapped[list["GeneRegulation"]] = relationship(back_populates="tf", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TF {self.name}>"


class GeneRegulation(Base):
    __tablename__ = "gene_regulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("genes.id"), nullable=False, index=True)
    tf_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transcription_factors.id"), nullable=False, index=True)
    regulation_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'activator', 'repressor', 'dual'
    confidence_score: Mapped[float | None] = mapped_column(Float)
    evidence_level: Mapped[str | None] = mapped_column(String(50))  # 'strong', 'weak', 'confirmed'
    source_db: Mapped[str | None] = mapped_column(String(50), default="RegulonDB")

    # Relationships
    gene: Mapped["Gene"] = relationship(back_populates="regulations")
    tf: Mapped["TranscriptionFactor"] = relationship(back_populates="regulations")

    def __repr__(self) -> str:
        return f"<Regulation {self.tf_id} -> {self.gene_id} ({self.regulation_type})>"
