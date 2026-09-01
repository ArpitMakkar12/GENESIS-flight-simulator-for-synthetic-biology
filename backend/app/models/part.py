import uuid
from sqlalchemy import String, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GeneticPart(Base):
    __tablename__ = "genetic_parts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    part_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'promoter', 'rbs', 'cds', 'terminator'
    sequence: Mapped[str] = mapped_column(Text, nullable=False)
    source_registry: Mapped[str | None] = mapped_column(String(50))  # 'igem', 'ecocyc', 'custom'
    registry_id: Mapped[str | None] = mapped_column(String(100))
    measured_strength: Mapped[float | None] = mapped_column(Float)
    measurement_unit: Mapped[str | None] = mapped_column(String(50))
    annotations: Mapped[dict | None] = mapped_column(JSONB)
    sbol_uri: Mapped[str | None] = mapped_column(String(500))

    def __repr__(self) -> str:
        return f"<GeneticPart {self.name} ({self.part_type})>"
