from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlarmState
from app.schemas.common import Page


class DeviceAlarmIn(BaseModel):
    """Device-reported alarm ingest payload (R3).

    ``alarm_code`` is the packed 4-byte alarm code as a hex string, e.g.
    ``"0x01020304"``. The server decodes it into major_id / sub_section /
    fault_type / severity using the byte order documented on the router
    (byte 0 = major_id, byte 1 = sub_section, byte 2 = fault_type,
    byte 3 = severity -- big-endian, byte 0 most significant).
    ``triggered_at`` is the device-side timestamp, stored verbatim.
    """

    alarm_code: str
    triggered_at: datetime


class DeviceAlarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    major_id: int
    sub_section: int
    fault_type: int
    severity: int
    alarm_code: int
    state: AlarmState
    triggered_at: datetime
    resolved_at: datetime | None


class DeviceAlarmListOut(BaseModel):
    items: list[DeviceAlarmOut]
    page: Page
