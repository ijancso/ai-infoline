"""add tenant greeting

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenants', sa.Column('greeting', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('tenants', 'greeting')
