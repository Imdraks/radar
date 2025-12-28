"""Add radar_harvest_reports table

Revision ID: 013_radar_harvest_reports
Revises: 012_radar_features
Create Date: 2024-12-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '013_radar_harvest_reports'
down_revision = '012_radar_features'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    # ========================================================================
    # RADAR HARVEST REPORTS TABLE
    # Stores auto-harvest run reports (every 15 minutes)
    # ========================================================================
    if not table_exists('radar_harvest_reports'):
        op.create_table(
            'radar_harvest_reports',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('harvest_time', sa.DateTime(), nullable=True),
            sa.Column('sources_scanned', sa.Integer(), default=0),
            sa.Column('items_fetched', sa.Integer(), default=0),
            sa.Column('items_new', sa.Integer(), default=0),
            sa.Column('items_duplicate', sa.Integer(), default=0),
            sa.Column('opportunities_created', sa.Integer(), default=0),
            sa.Column('opportunities_excellent', sa.Integer(), default=0),
            sa.Column('opportunities_good', sa.Integer(), default=0),
            sa.Column('opportunities_average', sa.Integer(), default=0),
            sa.Column('opportunities_poor', sa.Integer(), default=0),
            sa.Column('notifications_sent', sa.Integer(), default=0),
            sa.Column('duration_seconds', sa.Float(), default=0),
            sa.Column('status', sa.String(50), default='pending'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_radar_harvest_reports_time', 'radar_harvest_reports', ['harvest_time'])
        op.create_index('ix_radar_harvest_reports_status', 'radar_harvest_reports', ['status'])


def downgrade():
    if table_exists('radar_harvest_reports'):
        op.drop_index('ix_radar_harvest_reports_status', table_name='radar_harvest_reports')
        op.drop_index('ix_radar_harvest_reports_time', table_name='radar_harvest_reports')
        op.drop_table('radar_harvest_reports')
