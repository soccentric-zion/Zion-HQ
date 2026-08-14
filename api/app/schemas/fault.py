from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import FaultSeverity
from app.schemas.common import Page


class FaultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    code: str
    severity: FaultSeverity
    message: str
    raised_at: datetime
    cleared_at: datetime | None


class FaultListOut(BaseModel):
    items: list[FaultOut]
    page: Page
