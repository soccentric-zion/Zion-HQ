from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.enums import UserRole
from app.models.telemetry import TelemetrySample
from app.schemas.telemetry import TelemetrySampleIn, TelemetrySampleOut
from app.services.device_scope import get_tenant_device_or_404
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/devices/{device_id}/telemetry", tags=["telemetry"])

# location is reported via the same TelemetrySample table but isn't a
# chartable numeric metric -- excluded from the general series response.
_EXCLUDED_METRICS = {"location"}


@router.get("")
async def get_telemetry(
    device_id: UUID,
    metric: str | None = Query(default=None),
    points_per_metric: int = Query(default=200, le=2000),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    await get_tenant_device_or_404(db, ctx, device_id)

    stmt = select(TelemetrySample).where(TelemetrySample.device_id == device_id)
    if metric:
        stmt = stmt.where(TelemetrySample.metric == metric)
    else:
        stmt = stmt.where(TelemetrySample.metric.not_in(_EXCLUDED_METRICS))
    stmt = stmt.order_by(TelemetrySample.recorded_at.desc()).limit(points_per_metric * 20)

    samples = (await db.execute(stmt)).scalars().all()

    series: dict[str, list[dict]] = {}
    for sample in samples:
        bucket = series.setdefault(sample.metric, [])
        if len(bucket) < points_per_metric:
            bucket.append({"recorded_at": sample.recorded_at.isoformat(), "value": sample.value})

    for bucket in series.values():
        bucket.reverse()  # oldest -> newest for chart rendering
    return series


@router.post("", response_model=TelemetrySampleOut, status_code=status.HTTP_201_CREATED)
async def ingest_sample(
    device_id: UUID,
    body: TelemetrySampleIn,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """Ingest a single metric sample for a device (R3).

    The device must belong to the caller's tenant (scoped via the parent
    device), so a tenant can only write telemetry for its own devices. The
    device-side `recorded_at` is stored verbatim.
    """
    await get_tenant_device_or_404(db, ctx, device_id)

    sample = TelemetrySample(
        device_id=device_id,
        recorded_at=body.recorded_at,
        metric=body.metric,
        value=body.value,
        tags=body.tags,
    )
    db.add(sample)
    await db.flush()
    await db.commit()
    await db.refresh(sample)
    return TelemetrySampleOut.model_validate(sample)


@router.get("/{sample_id}", response_model=TelemetrySampleOut)
async def get_sample(
    device_id: UUID,
    sample_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    """Return a single raw sample by id, scoped to the device (R3).

    Unlike the series GET, this returns the full stored row field-for-field,
    which is what the POST-then-GET equality contract in R3 needs.
    """
    await get_tenant_device_or_404(db, ctx, device_id)

    stmt = select(TelemetrySample).where(
        TelemetrySample.id == sample_id,
        TelemetrySample.device_id == device_id,
    )
    sample = (await db.execute(stmt)).scalar_one_or_none()
    if sample is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "telemetry sample not found")
    return TelemetrySampleOut.model_validate(sample)
