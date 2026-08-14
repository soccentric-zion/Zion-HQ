import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AlarmState
from app.models.mixins import UUIDPKMixin


class DeviceAlarm(Base, UUIDPKMixin):
    """A device-reported alarm stored in the literal ``alarms`` table (R3
    ingest path).

    This is distinct from the rule-based ``alarm`` table
    (``app.models.alarm.Alarm``), which records alarms raised by
    operator-configured ``AlarmRule`` rows. Device-reported alarms carry the
    packed 4-byte alarm code emitted by the device's alarms daemon plus its
    decoded fields, and have no originating rule.

    Byte order of ``alarm_code`` (big-endian uint32, byte 0 = most significant):
      byte 0 = major_id, byte 1 = sub_section,
      byte 2 = fault_type, byte 3 = severity.
    Example: 0x01020304 -> major_id=1, sub_section=2, fault_type=3, severity=4.
    This byte order MUST match the daemon's ``alarms_encode`` packing.
    """

    __tablename__ = "alarms"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), index=True
    )
    # 4-byte alarm scheme fields (each a single byte, 0..255).
    major_id: Mapped[int] = mapped_column(SmallInteger)
    sub_section: Mapped[int] = mapped_column(SmallInteger)
    fault_type: Mapped[int] = mapped_column(SmallInteger)
    severity: Mapped[int] = mapped_column(SmallInteger)
    # The raw packed 4-byte code, stored for traceability/round-trip checks.
    # BigInteger (not Integer): the 4-byte code is unsigned and 0xFFFFFFFF
    # (4294967295) overflows Postgres INTEGER (int32, max ~2.1e9).
    alarm_code: Mapped[int] = mapped_column(BigInteger)
    # Reuse the existing AlarmState enum so `clear` can set it to `resolved`.
    state: Mapped[AlarmState] = mapped_column(
        Enum(AlarmState, name="alarm_state"), default=AlarmState.active, index=True
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
