import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CommandKind
from app.models.mixins import TimestampMixin, UUIDPKMixin


class PendingCommand(Base, UUIDPKMixin, TimestampMixin):
    """Cross-process handoff for ops commands: the REST API and
    agent-gateway are separate deployables (ARCHITECTURE.md §2) with no
    direct RPC between them, so a command an operator triggers via the API
    is delivered to the device by agent-gateway picking it up here on the
    device's next heartbeat, not pushed synchronously.
    """

    __tablename__ = "pending_command"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), index=True
    )
    # Correlates back to this row via CommandAck.command_id -- see
    # agent-gateway/gateway/handlers.py::handle_command_ack for the
    # "update:{rollout_id}" / "restore:{backup_id}" encoding.
    command_id: Mapped[str] = mapped_column(unique=True, index=True)
    kind: Mapped[CommandKind] = mapped_column(Enum(CommandKind, name="command_kind"))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
