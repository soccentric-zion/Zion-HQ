import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPKMixin


class LogBundle(Base, UUIDPKMixin):
    __tablename__ = "log_bundle"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), index=True
    )
    storage_url: Mapped[str]
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    time_range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    time_range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
