from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Page


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    target_device_id: UUID | None
    payload: dict
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: list[AuditLogOut]
    page: Page
