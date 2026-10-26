from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Plot(Base):
    __tablename__ = "plots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"))
    crop: Mapped[str] = mapped_column(String(64), default="citrus")
    stage: Mapped[str] = mapped_column(String(64), default="fruit_growth")
    irrigation_method: Mapped[str] = mapped_column(String(32), default="drip")
    area_ha: Mapped[float] = mapped_column(Float, default=0.0)
    last_irrigation_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    geom = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("Farmer", back_populates="plots")
    recommendations = relationship("Recommendation", back_populates="plot")
