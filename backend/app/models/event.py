from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False, default="motion")
    snapshot_path: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrichment_status: Mapped[str | None] = mapped_column(
        String, nullable=True, default="pending"
    )
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
