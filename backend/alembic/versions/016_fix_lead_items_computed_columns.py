"""Remove computed columns from lead_items table

These columns (has_contact, has_deadline, budget_display) are now computed via @property
in the SQLAlchemy model and should not be stored in the database.

Revision ID: 016_fix_lead_items_computed_columns
Revises: 015_add_two_factor_columns
Create Date: 2025-12-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = '016_fix_lead_items_computed_columns'
down_revision = '015_add_two_factor_columns'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if column exists in table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Remove computed columns from lead_items if they exist
    # These are now @property in the model
    
    if column_exists('lead_items', 'has_contact'):
        op.drop_column('lead_items', 'has_contact')
    
    if column_exists('lead_items', 'has_deadline'):
        op.drop_column('lead_items', 'has_deadline')
    
    if column_exists('lead_items', 'budget_display'):
        op.drop_column('lead_items', 'budget_display')


def downgrade() -> None:
    # Re-add columns if needed (optional)
    op.add_column('lead_items', sa.Column('has_contact', sa.Boolean(), server_default='false'))
    op.add_column('lead_items', sa.Column('has_deadline', sa.Boolean(), server_default='false'))
    op.add_column('lead_items', sa.Column('budget_display', sa.String(100), nullable=True))
