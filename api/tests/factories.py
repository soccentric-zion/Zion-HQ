import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import SESSION_COOKIE_NAME
from app.auth.session import issue_session_token
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User


async def make_tenant(session: AsyncSession, name: str | None = None) -> Tenant:
    tenant = Tenant(name=name or f"tenant-{uuid.uuid4().hex[:8]}")
    session.add(tenant)
    await session.flush()
    return tenant


async def make_user(
    session: AsyncSession, tenant: Tenant, role: UserRole, email: str | None = None
) -> User:
    user = User(
        tenant_id=tenant.id,
        email=email or f"{role.value}-{uuid.uuid4().hex[:8]}@example.com",
        role=role,
        auth_subject_id=f"sub-{uuid.uuid4().hex[:8]}",
    )
    session.add(user)
    await session.flush()
    return user


def login_as(client: AsyncClient, user: User) -> None:
    token = issue_session_token(user.id, user.tenant_id, user.role.value)
    client.cookies.set(SESSION_COOKIE_NAME, token)
