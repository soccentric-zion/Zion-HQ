from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


class UserInvite(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.viewer


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    created_at: datetime
    # auth_subject_id deliberately excluded -- internal auth linkage, not
    # application data (see python/fastapi.md: never leak internal auth state).
