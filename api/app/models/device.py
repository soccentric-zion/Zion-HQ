from datetime import datetime

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PairingState
from app.models.mixins import TenantScopedMixin

if TYPE_CHECKING:
    from app.models.device_credential import DeviceCredential


class Device(Base, TenantScopedMixin):
    __tablename__ = "device"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_device_tenant_name"),)

    name: Mapped[str] = mapped_column(index=True)
    pairing_state: Mapped[PairingState] = mapped_column(
        Enum(PairingState, name="pairing_state"), default=PairingState.pending, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Hardware identity, populated once the device actually pairs (Phase 2)
    # from Zion-Configuration's board manifest -- absent for pre-provisioned
    # (pending) devices.
    serial: Mapped[str | None] = mapped_column(nullable=True)
    board_rev: Mapped[str | None] = mapped_column(nullable=True)

    credentials: Mapped[list["DeviceCredential"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
