import uuid
from sqlalchemy import String, Integer, Float, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Gene(Base):
    __tablename__ = "genes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locus_tag: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), index=True)
    product: Mapped[str | None] = mapped_column(String(500))
    start_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    end_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    strand: Mapped[str] = mapped_column(String(1), nullable=False)  # '+' or '-'
    dna_sequence: Mapped[str | None] = mapped_column(Text)
    protein_sequence: Mapped[str | None] = mapped_column(Text)
    cog_category: Mapped[str | None] = mapped_column(String(10))
    gc_content: Mapped[float | None] = mapped_column(Float)
    length_bp: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    regulations: Mapped[list["GeneRegulation"]] = relationship(back_populates="gene", lazy="selectin")
    enzyme_reactions: Mapped[list["EnzymeReaction"]] = relationship(back_populates="gene", lazy="selectin")
    transporter: Mapped["Transporter | None"] = relationship(back_populates="gene", lazy="selectin")

    __table_args__ = (
        Index("idx_gene_product_fts", "product"),
    )

    def __repr__(self) -> str:
        return f"<Gene {self.locus_tag} ({self.name})>"
