import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Construct(Base):
    __tablename__ = "constructs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    full_sequence: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    # Relationships
    parts: Mapped[list["ConstructPart"]] = relationship(back_populates="construct", lazy="selectin", cascade="all, delete-orphan")
    simulations: Mapped[list["Simulation"]] = relationship(back_populates="construct", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Construct {self.name} v{self.version}>"


class ConstructPart(Base):
    __tablename__ = "construct_parts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    construct_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constructs.id", ondelete="CASCADE"), nullable=False)
    part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("genetic_parts.id"), nullable=False)
    position_order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_pos: Mapped[int | None] = mapped_column(Integer)
    end_pos: Mapped[int | None] = mapped_column(Integer)
    orientation: Mapped[str] = mapped_column(String(10), default="forward")  # 'forward', 'reverse'

    # Relationships
    construct: Mapped["Construct"] = relationship(back_populates="parts")
    part: Mapped["GeneticPart"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<ConstructPart pos={self.position_order}>"
