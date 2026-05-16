"""add call_messages and recordings tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", UUID(as_uuid=True), sa.ForeignKey("calls.id"), nullable=False),
        sa.Column("call_sid", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_call_messages_call_sid", "call_messages", ["call_sid"])

    op.create_table(
        "recordings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("call_sid", sa.String(64), nullable=False),
        sa.Column("recording_sid", sa.String(64), nullable=False, unique=True),
        sa.Column("spaces_key", sa.String(256), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_recordings_call_sid", "recordings", ["call_sid"])


def downgrade() -> None:
    op.drop_index("ix_recordings_call_sid", table_name="recordings")
    op.drop_table("recordings")
    op.drop_index("ix_call_messages_call_sid", table_name="call_messages")
    op.drop_table("call_messages")
