from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SanitizeOrder(Base):
    __tablename__ = "sanitize_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False)  # uv | chemical
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    operator_name: Mapped[str] = mapped_column(String(64), nullable=False)
    planned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    room: Mapped["Room"] = relationship("Room", back_populates="sanitize_orders")
