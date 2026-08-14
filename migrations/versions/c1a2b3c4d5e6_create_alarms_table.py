"""create alarms table for device-reported 4-byte alarms

Revision ID: c1a2b3c4d5e6
Revises: a40971629062
Create Date: 2026-07-30 00:00:00.000000

Creates the literal ``alarms`` table backing
``app.models.device_alarm.DeviceAlarm`` for device-reported alarms (loop
20260730-app-alarms-daemon, R3 ingest path). This is a NEW table, distinct
from the pre-existing rule-based ``alarm`` table (phase1) -- the ``alarm``
table is NOT touched by this migration.

Columns: device_id (FK device.id CASCADE, indexed), the 4-byte alarm scheme
fields major_id / sub_section / fault_type / severity (SmallInteger, each a
single byte), alarm_code (BigInteger -- the raw packed 4-byte code; unsigned
0xFFFFFFFF overflows int32), state (Enum alarm_state, default active,
indexed -- reuses the existing enum), triggered_at, resolved_at (nullable).

Byte order of ``alarm_code`` (big-endian uint32, byte 0 = most significant):
  byte 0 = major_id, byte 1 = sub_section,
  byte 2 = fault_type, byte 3 = severity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'a40971629062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'alarms',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.UUID(), nullable=False),
        sa.Column('major_id', sa.SmallInteger(), nullable=False),
        sa.Column('sub_section', sa.SmallInteger(), nullable=False),
        sa.Column('fault_type', sa.SmallInteger(), nullable=False),
        sa.Column('severity', sa.SmallInteger(), nullable=False),
        # BigInteger: the 4-byte code is unsigned; 0xFFFFFFFF overflows int32.
        sa.Column('alarm_code', sa.BigInteger(), nullable=False),
        sa.Column(
            'state',
            sa.Enum('active', 'acknowledged', 'resolved', name='alarm_state'),
            nullable=False,
        ),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['device.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_alarms_device_id'), 'alarms', ['device_id'], unique=False)
    op.create_index(op.f('ix_alarms_state'), 'alarms', ['state'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_alarms_state'), table_name='alarms')
    op.drop_index(op.f('ix_alarms_device_id'), table_name='alarms')
    op.drop_table('alarms')