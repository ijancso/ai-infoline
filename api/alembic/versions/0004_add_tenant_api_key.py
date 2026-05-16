"""add api_key to tenants

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("api_key", UUID(as_uuid=True), nullable=True),
    )
    op.execute("UPDATE tenants SET api_key = gen_random_uuid() WHERE api_key IS NULL")
    op.alter_column("tenants", "api_key", nullable=False)
    op.create_index("ix_tenants_api_key", "tenants", ["api_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenants_api_key", table_name="tenants")
    op.drop_column("tenants", "api_key")
