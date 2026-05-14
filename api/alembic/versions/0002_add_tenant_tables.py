"""add tenant and phone_numbers tables, tenant_id on calls

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("stripe_customer_id", sa.String(64), nullable=True, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "phone_numbers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False, unique=True),
        sa.Column("label", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_phone_numbers_phone_number", "phone_numbers", ["phone_number"])

    op.add_column(
        "calls",
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calls", "tenant_id")
    op.drop_index("ix_phone_numbers_phone_number", table_name="phone_numbers")
    op.drop_table("phone_numbers")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
