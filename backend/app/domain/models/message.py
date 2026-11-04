from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Message(Base):
    """Outbound notification / Ask channel log (Backend seat)."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farmer_id: Mapped[int | None] = mapped_column(ForeignKey("farmers.id"), nullable=True)
    plot_id: Mapped[int | None] = mapped_column(ForeignKey("plots.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), default="web")
    direction: Mapped[str] = mapped_column(String(16), default="outbound")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
