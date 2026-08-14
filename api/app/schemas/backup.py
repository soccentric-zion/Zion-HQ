from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Page


class BackupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    size_bytes: int
    created_at: datetime
    restored_at: datetime | None


class BackupListOut(BaseModel):
    items: list[BackupOut]
    page: Page
