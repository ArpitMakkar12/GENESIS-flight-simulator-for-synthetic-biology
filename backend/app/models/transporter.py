import uuid
from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transporter(Base):
    __tablename__ = "transporters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("genes.id"), nullable=False, index=True)
    tcdb_id: Mapped[str | None] = mapped_column(String(20))
    tc_family: Mapped[str | None] = mapped_column(String(100))
    substrate: Mapped[str | None] = mapped_column(String(200))
    substrate_chebi_id: Mapped[str | None] = mapped_column(String(20), index=True)
    transport_type: Mapped[str | None] = mapped_column(String(50))  # 'ABC', 'PTS', 'MFS', etc.
    vmax: Mapped[float | None] = mapped_column(Float)
    km_transport: Mapped[float | None] = mapped_column(Float)
    atp_cost: Mapped[int | None] = mapped_column(Integer, default=1)

    # Relationships
    gene: Mapped["Gene"] = relationship(back_populates="transporter")

    def __repr__(self) -> str:
        return f"<Transporter {self.tcdb_id} substrate={self.substrate}>"
