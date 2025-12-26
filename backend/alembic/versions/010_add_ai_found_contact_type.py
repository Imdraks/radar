"""Add AI_FOUND to ContactType enum

Revision ID: 010_add_ai_found
Revises: 009_entity_brief_system
Create Date: 2025-12-26

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '010_add_ai_found'
down_revision = '009_entity_brief_system'
branch_labels = None
depends_on = None


def upgrade():
    # Add AI_FOUND value to the contacttype enum
    op.execute("ALTER TYPE contacttype ADD VALUE IF NOT EXISTS 'AI_FOUND'")


def downgrade():
    # PostgreSQL doesn't support removing enum values easily
    # This is a no-op for downgrade
    pass
