"""Tenant-scoping enforcement point.

IMPLEMENTATION_PLAN §6: "the single most important invariant in the whole
system." Every read/write of a tenant-owned table goes through here so a
handler *cannot* forget the `tenant_id` filter -- there is no direct-query
escape hatch in the routers for tenant-scoped models.
"""

from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mixins import TenantScopedMixin

ModelT = TypeVar("ModelT", bound=TenantScopedMixin)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    user_id: UUID
    role: str


class TenantRepo:
    """Bound to one request's TenantContext; every query it builds is
    pre-filtered to that tenant."""

    def __init__(self, session: AsyncSession, ctx: TenantContext):
        self.session = session
        self.ctx = ctx

    def scoped(self, model: type[ModelT]) -> Select:
        return select(model).where(model.tenant_id == self.ctx.tenant_id)

    async def get_or_404(self, model: type[ModelT], obj_id: UUID) -> ModelT | None:
        result = await self.session.execute(self.scoped(model).where(model.id == obj_id))
        return result.scalar_one_or_none()

    def stamp_tenant(self, obj: ModelT) -> ModelT:
        obj.tenant_id = self.ctx.tenant_id
        return obj
