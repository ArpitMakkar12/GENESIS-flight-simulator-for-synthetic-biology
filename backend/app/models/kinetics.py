import uuid
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EnzymeKinetics(Base):
    __tablename__ = "enzyme_kinetics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reactions.id"), nullable=False, index=True)
    ec_number: Mapped[str | None] = mapped_column(String(20), index=True)
    km_value: Mapped[float | None] = mapped_column(Float)  # mM
    kcat_value: Mapped[float | None] = mapped_column(Float)  # s^-1
    optimal_temp: Mapped[float | None] = mapped_column(Float)  # Celsius
    optimal_ph: Mapped[float | None] = mapped_column(Float)
    temp_stability_min: Mapped[float | None] = mapped_column(Float)
    temp_stability_max: Mapped[float | None] = mapped_column(Float)
    ph_stability_min: Mapped[float | None] = mapped_column(Float)
    ph_stability_max: Mapped[float | None] = mapped_column(Float)
    organism_source: Mapped[str | None] = mapped_column(String(200))
    brenda_id: Mapped[str | None] = mapped_column(String(50))
    activity_curve_temp: Mapped[dict | None] = mapped_column(JSONB)  # [{"temp": 25, "activity": 0.6}, ...]
    activity_curve_ph: Mapped[dict | None] = mapped_column(JSONB)    # [{"ph": 5.0, "activity": 0.3}, ...]

    # Relationships
    reaction: Mapped["Reaction"] = relationship(back_populates="kinetics")

    def __repr__(self) -> str:
        return f"<EnzymeKinetics EC:{self.ec_number} Km={self.km_value} kcat={self.kcat_value}>"
