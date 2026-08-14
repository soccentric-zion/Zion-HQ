from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlarmState


class AlarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alarm_rule_id: UUID
    device_id: UUID
    state: AlarmState
    triggered_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class AlarmRuleCreate(BaseModel):
    name: str
    condition: dict
    notify_channels: dict = {}
    enabled: bool = True


class AlarmRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    condition: dict
    notify_channels: dict
    enabled: bool
