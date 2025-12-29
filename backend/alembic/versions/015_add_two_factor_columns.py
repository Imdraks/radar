"""Add two-factor authentication columns to users

Revision ID: 015_add_two_factor_columns
Revises: 014_performance_indexes
Create Date: 2024-12-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '015_add_two_factor_columns'
down_revision = '014_performance_indexes'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # Add two-factor authentication columns to users table
    if not column_exists('users', 'two_factor_enabled'):
        op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), server_default='false', nullable=False))
    
    if not column_exists('users', 'two_factor_secret'):
        op.add_column('users', sa.Column('two_factor_secret', sa.String(255), nullable=True))
    
    if not column_exists('users', 'backup_codes'):
        op.add_column('users', sa.Column('backup_codes', sa.JSON(), nullable=True))
    
    if not column_exists('users', 'last_login_at'):
        op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    if column_exists('users', 'last_login_at'):
        op.drop_column('users', 'last_login_at')
    if column_exists('users', 'backup_codes'):
        op.drop_column('users', 'backup_codes')
    if column_exists('users', 'two_factor_secret'):
        op.drop_column('users', 'two_factor_secret')
    if column_exists('users', 'two_factor_enabled'):
        op.drop_column('users', 'two_factor_enabled')
