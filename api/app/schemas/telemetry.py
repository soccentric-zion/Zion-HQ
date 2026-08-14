from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TelemetryPointOut(BaseModel):
    recorded_at: datetime
    value: float


class TelemetrySampleIn(BaseModel):
    """A single metric sample POSTed by a device or operator.

    `recorded_at` is the device-side timestamp; the server does not rewrite it
    so a sample captured during a network partition retains its true time.
    """

    recorded_at: datetime
    metric: str
    value: float
    tags: dict[str, Any] = {}


class TelemetrySampleOut(BaseModel):
    """The full stored row, returned after ingest and by sample-id lookup.

    `from_attributes` lets this build straight from the ORM model without a
    manual field-copy, so the GET-by-id response is field-for-field faithful
    to what was committed (R3 contract).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    recorded_at: datetime
    metric: str
    value: float
    tags: dict[str, Any]
