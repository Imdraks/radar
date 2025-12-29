"""
Initial migration - Create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types first
    role_enum = postgresql.ENUM('ADMIN', 'BIZDEV', 'PM', 'VIEWER', name='role', create_type=False)
    role_enum.create(op.get_bind(), checkfirst=True)
    
    sourcetype_enum = postgresql.ENUM('EMAIL', 'RSS', 'HTML', 'API', name='sourcetype', create_type=False)
    sourcetype_enum.create(op.get_bind(), checkfirst=True)
    
    opportunitycategory_enum = postgresql.ENUM(
        'PUBLIC_TENDER', 'CALL_FOR_PROJECTS', 'GRANT', 'PARTNERSHIP', 'VENUE', 'SUPPLIER', 'OTHER',
        name='opportunitycategory', create_type=False
    )
    opportunitycategory_enum.create(op.get_bind(), checkfirst=True)
    
    opportunitystatus_enum = postgresql.ENUM(
        'NEW', 'REVIEW', 'QUALIFIED', 'IN_PROGRESS', 'SUBMITTED', 'WON', 'LOST', 'ARCHIVED',
        name='opportunitystatus', create_type=False
    )
    opportunitystatus_enum.create(op.get_bind(), checkfirst=True)
    
    taskstatus_enum = postgresql.ENUM('TODO', 'IN_PROGRESS', 'DONE', 'CANCELLED', name='taskstatus', create_type=False)
    taskstatus_enum.create(op.get_bind(), checkfirst=True)
    
    ruletype_enum = postgresql.ENUM('URGENCY', 'EVENT_FIT', 'QUALITY', 'VALUE', 'PENALTY', name='ruletype', create_type=False)
    ruletype_enum.create(op.get_bind(), checkfirst=True)
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tracking_id', sa.String(length=15), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', postgresql.ENUM('ADMIN', 'BIZDEV', 'PM', 'VIEWER', name='role', create_type=False), server_default='VIEWER', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_superuser', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_whitelisted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('auth_provider', sa.String(length=50), server_default='credentials', nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('two_factor_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('two_factor_secret', sa.String(length=255), nullable=True),
        sa.Column('backup_codes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_tracking_id', 'users', ['tracking_id'], unique=True)
    
    # Source configs table
    op.create_table(
        'source_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_type', postgresql.ENUM('EMAIL', 'RSS', 'HTML', 'API', name='sourcetype', create_type=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('url', sa.String(length=2000), nullable=True),
        sa.Column('email_folder', sa.String(length=255), nullable=True),
        sa.Column('email_sender_filter', sa.String(length=255), nullable=True),
        sa.Column('html_selectors', sa.JSON(), nullable=True),
        sa.Column('api_headers', sa.JSON(), nullable=True),
        sa.Column('api_params', sa.JSON(), nullable=True),
        sa.Column('api_response_mapping', sa.JSON(), nullable=True),
        sa.Column('poll_interval_minutes', sa.Integer(), server_default='360', nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_items_fetched', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_errors', sa.Integer(), server_default='0', nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_source_configs_name', 'source_configs', ['name'], unique=True)
    op.create_index('ix_source_configs_source_type', 'source_configs', ['source_type'], unique=False)
    
    # Opportunities table
    op.create_table(
        'opportunities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('source_type', postgresql.ENUM('EMAIL', 'RSS', 'HTML', 'API', name='sourcetype', create_type=False), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('source_config_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('category', postgresql.ENUM('PUBLIC_TENDER', 'CALL_FOR_PROJECTS', 'GRANT', 'PARTNERSHIP', 'VENUE', 'SUPPLIER', 'OTHER', name='opportunitycategory', create_type=False), server_default='OTHER', nullable=True),
        sa.Column('organization', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('snippet', sa.String(length=500), nullable=True),
        sa.Column('url_primary', sa.String(length=2000), nullable=True),
        sa.Column('urls_all', sa.JSON(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deadline_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location_city', sa.String(length=100), nullable=True),
        sa.Column('location_region', sa.String(length=100), nullable=True),
        sa.Column('location_country', sa.String(length=2), server_default='FR', nullable=True),
        sa.Column('budget_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('budget_currency', sa.String(length=3), server_default='EUR', nullable=True),
        sa.Column('budget_hint', sa.String(length=500), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('contact_url', sa.String(length=2000), nullable=True),
        sa.Column('score', sa.Integer(), server_default='0', nullable=True),
        sa.Column('score_breakdown', sa.JSON(), nullable=True),
        sa.Column('status', postgresql.ENUM('NEW', 'REVIEW', 'QUALIFIED', 'IN_PROGRESS', 'SUBMITTED', 'WON', 'LOST', 'ARCHIVED', name='opportunitystatus', create_type=False), server_default='NEW', nullable=False),
        sa.Column('assigned_to_user_id', sa.Integer(), nullable=True),
        sa.Column('possible_duplicate', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('duplicate_of_id', sa.Integer(), nullable=True),
        sa.Column('raw_content_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['duplicate_of_id'], ['opportunities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_config_id'], ['source_configs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_opportunities_external_id', 'opportunities', ['external_id'], unique=True)
    op.create_index('ix_opportunities_status', 'opportunities', ['status'], unique=False)
    op.create_index('ix_opportunities_category', 'opportunities', ['category'], unique=False)
    op.create_index('ix_opportunities_location_region', 'opportunities', ['location_region'], unique=False)
    op.create_index('ix_opportunities_organization', 'opportunities', ['organization'], unique=False)
    op.create_index('ix_opportunities_score', 'opportunities', ['score'], unique=False)
    op.create_index('ix_opportunities_deadline_at', 'opportunities', ['deadline_at'], unique=False)
    op.create_index('ix_opportunities_url_primary', 'opportunities', ['url_primary'], unique=False)
    op.create_index('ix_opportunities_budget_amount', 'opportunities', ['budget_amount'], unique=False)
    op.create_index('ix_opportunities_source_name', 'opportunities', ['source_name'], unique=False)
    # Composite indexes
    op.create_index('ix_opportunities_score_deadline', 'opportunities', ['score', 'deadline_at'], unique=False)
    op.create_index('ix_opportunities_status_score', 'opportunities', ['status', 'score'], unique=False)
    op.create_index('ix_opportunities_created_status', 'opportunities', ['created_at', 'status'], unique=False)
    
    # Opportunity tags table (reusable tags)
    op.create_table(
        'opportunity_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=7), server_default='#6366f1', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_opportunity_tags_name', 'opportunity_tags', ['name'], unique=True)
    
    # Opportunity tag associations (many-to-many)
    op.create_table(
        'opportunity_tag_associations',
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id']),
        sa.ForeignKeyConstraint(['tag_id'], ['opportunity_tags.id']),
        sa.PrimaryKeyConstraint('opportunity_id', 'tag_id'),
    )
    
    # Opportunity notes table
    op.create_table(
        'opportunity_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Opportunity tasks table
    op.create_table(
        'opportunity_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM('TODO', 'IN_PROGRESS', 'DONE', 'CANCELLED', name='taskstatus', create_type=False), server_default='TODO', nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create ingestionstatus ENUM
    op.execute("CREATE TYPE ingestionstatus AS ENUM ('PENDING', 'RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED')")
    
    # Ingestion runs table
    op.create_table(
        'ingestion_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_config_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED', name='ingestionstatus', create_type=False), server_default='PENDING', nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('items_fetched', sa.Integer(), server_default='0', nullable=True),
        sa.Column('items_new', sa.Integer(), server_default='0', nullable=True),
        sa.Column('items_duplicate', sa.Integer(), server_default='0', nullable=True),
        sa.Column('items_updated', sa.Integer(), server_default='0', nullable=True),
        sa.Column('items_error', sa.Integer(), server_default='0', nullable=True),
        sa.Column('errors', sa.JSON(), server_default='[]', nullable=True),
        sa.Column('run_metadata', sa.JSON(), server_default='{}', nullable=True),
        sa.ForeignKeyConstraint(['source_config_id'], ['source_configs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ingestion_runs_started_at', 'ingestion_runs', ['started_at'], unique=False)
    op.create_index('ix_ingestion_runs_status', 'ingestion_runs', ['status'], unique=False)
    
    # Scoring rules table
    op.create_table(
        'scoring_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', postgresql.ENUM('URGENCY', 'EVENT_FIT', 'QUALITY', 'VALUE', 'PENALTY', name='ruletype', create_type=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('condition_type', sa.String(length=100), nullable=False),
        sa.Column('condition_value', sa.JSON(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.Integer(), server_default='50', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scoring_rules_name', 'scoring_rules', ['name'], unique=True)
    op.create_index('ix_scoring_rules_rule_type', 'scoring_rules', ['rule_type'], unique=False)


def downgrade() -> None:
    op.drop_table('scoring_rules')
    op.drop_table('ingestion_runs')
    op.drop_table('opportunity_tasks')
    op.drop_table('opportunity_notes')
    op.drop_table('opportunity_tag_associations')
    op.drop_table('opportunity_tags')
    op.drop_table('opportunities')
    op.drop_table('source_configs')
    op.drop_table('users')
    
    # Drop ENUM types
    op.execute('DROP TYPE IF EXISTS ingestionstatus')
    op.execute('DROP TYPE IF EXISTS ruletype')
    op.execute('DROP TYPE IF EXISTS taskstatus')
    op.execute('DROP TYPE IF EXISTS opportunitystatus')
    op.execute('DROP TYPE IF EXISTS opportunitycategory')
    op.execute('DROP TYPE IF EXISTS sourcetype')
    op.execute('DROP TYPE IF EXISTS role')
