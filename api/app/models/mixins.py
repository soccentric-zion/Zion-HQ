import uuid
from datetime import datetime, UTC

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TenantScopedMixin(UUIDPKMixin, TimestampMixin):
    """Every tenant-owned table gets `tenant_id` this way -- never ad hoc.

    IMPLEMENTATION_PLAN §6: "the single most important invariant in the
    whole system." Query-layer enforcement lives in
    app/services/tenant_repo.py, not here -- this mixin only guarantees the
    column exists and is indexed/foreign-keyed.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), index=True
    )
