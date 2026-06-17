"""add tenant knowledge base

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenants', sa.Column('knowledge_base', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('tenants', 'knowledge_base')
