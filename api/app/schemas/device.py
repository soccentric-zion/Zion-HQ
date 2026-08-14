from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import PairingState
from app.schemas.common import Page


class DeviceCreate(BaseModel):
    name: str


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    pairing_state: PairingState
    online: bool
    last_seen_at: datetime | None
    serial: str | None
    board_rev: str | None
    created_at: datetime


class DeviceListOut(BaseModel):
    items: list[DeviceOut]
    page: Page


class DeviceCreateOut(BaseModel):
    device: DeviceOut
    # Only present in Phase 2+ once pairing-token generation exists; Phase 1
    # creates an inert `pending` record only (IMPLEMENTATION_PLAN §1.3).
    pairing_token: str | None = None


class BulkProvisionCreate(BaseModel):
    names: list[str]


class BulkProvisionedDevice(BaseModel):
    device: DeviceOut
    pairing_token: str


class BulkProvisionOut(BaseModel):
    items: list[BulkProvisionedDevice]


class LocationOut(BaseModel):
    lat: float | None = None
    lon: float | None = None
    accuracy_m: float | None = None
    source: str | None = None
    recorded_at: datetime | None = None
