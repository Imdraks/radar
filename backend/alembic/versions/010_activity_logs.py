"""Add activity logs and user tracking_id

Revision ID: 010_activity_logs
Revises: 009_entity_brief_system
Create Date: 2024-12-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '010_activity_logs'
down_revision = '009_entity_brief_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tracking_id to users table
    op.add_column('users', sa.Column('tracking_id', sa.String(15), nullable=True))
    op.create_index('ix_users_tracking_id', 'users', ['tracking_id'], unique=True)
    
    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_tracking_id', sa.String(10), nullable=False, index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', sa.JSON, nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table('activity_logs')
    op.drop_index('ix_users_tracking_id', table_name='users')
    op.drop_column('users', 'tracking_id')
