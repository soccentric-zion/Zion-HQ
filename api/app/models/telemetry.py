import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPKMixin


class TelemetrySample(Base, UUIDPKMixin):
    __tablename__ = "telemetry_sample"
    __table_args__ = (
        Index("ix_telemetry_device_metric_time", "device_id", "metric", "recorded_at"),
    )

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metric: Mapped[str] = mapped_column(index=True)
    value: Mapped[float] = mapped_column(Float)
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)
