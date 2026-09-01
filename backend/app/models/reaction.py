import uuid
from sqlalchemy import String, Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Reaction(Base):
    __tablename__ = "reactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bigg_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(500))
    subsystem: Mapped[str | None] = mapped_column(String(200))
    reaction_formula: Mapped[str | None] = mapped_column(String(1000))
    default_lower_bound: Mapped[float] = mapped_column(Float, default=-1000.0)
    default_upper_bound: Mapped[float] = mapped_column(Float, default=1000.0)
    is_reversible: Mapped[bool] = mapped_column(Boolean, default=True)
    ec_number: Mapped[str | None] = mapped_column(String(20))

    # Relationships
    enzyme_reactions: Mapped[list["EnzymeReaction"]] = relationship(back_populates="reaction", lazy="selectin")
    kinetics: Mapped[list["EnzymeKinetics"]] = relationship(back_populates="reaction", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Reaction {self.bigg_id}>"


class EnzymeReaction(Base):
    __tablename__ = "enzyme_reactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("genes.id"), nullable=False, index=True)
    reaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reactions.id"), nullable=False, index=True)
    gpr_rule: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    gene: Mapped["Gene"] = relationship(back_populates="enzyme_reactions")
    reaction: Mapped["Reaction"] = relationship(back_populates="enzyme_reactions")

    def __repr__(self) -> str:
        return f"<EnzymeReaction gene={self.gene_id} reaction={self.reaction_id}>"
