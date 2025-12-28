"""Radar Features: Profiles, Shortlists, Clusters, Deadline Alerts, Source Health, Contact Finder

Revision ID: 012_radar_features
Revises: 011c_merge_heads
Create Date: 2024-12-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '012_radar_features'
down_revision = '011c_merge_heads'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    # ========================================================================
    # PROFILES TABLE
    # ========================================================================
    if not table_exists('profiles'):
        op.create_table(
            'profiles',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('keywords_include', postgresql.ARRAY(sa.String()), default=[]),
            sa.Column('keywords_exclude', postgresql.ARRAY(sa.String()), default=[]),
            sa.Column('regions', postgresql.ARRAY(sa.String()), default=[]),
            sa.Column('cities', postgresql.ARRAY(sa.String()), default=[]),
            sa.Column('budget_min', sa.Numeric(15, 2), nullable=True),
            sa.Column('budget_max', sa.Numeric(15, 2), nullable=True),
            sa.Column('objectives', postgresql.ARRAY(sa.String()), default=[]),
            sa.Column('weights', postgresql.JSON(), default={}),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('ix_profiles_name', 'profiles', ['name'])
        op.create_index('ix_profiles_is_active', 'profiles', ['is_active'])

    # ========================================================================
    # OPPORTUNITY PROFILE SCORES TABLE
    # ========================================================================
    if not table_exists('opportunity_profile_scores'):
        op.create_table(
            'opportunity_profile_scores',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('fit_score', sa.Integer(), default=0),
            sa.Column('reasons', postgresql.JSON(), default={}),
            sa.Column('computed_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('opportunity_id', 'profile_id', name='uq_opportunity_profile')
        )
        op.create_index('ix_opp_profile_score', 'opportunity_profile_scores', ['profile_id', 'fit_score'])

    # ========================================================================
    # DAILY SHORTLISTS TABLE
    # ========================================================================
    if not table_exists('daily_shortlists'):
        op.create_table(
            'daily_shortlists',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('items', postgresql.JSON(), default=[]),
            sa.Column('total_candidates', sa.Integer(), default=0),
            sa.Column('items_count', sa.Integer(), default=0),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('date', 'profile_id', name='uq_daily_shortlist_date_profile')
        )
        op.create_index('ix_shortlist_date_profile', 'daily_shortlists', ['date', 'profile_id'])

    # ========================================================================
    # OPPORTUNITY CLUSTERS TABLE
    # ========================================================================
    if not table_exists('opportunity_clusters'):
        op.create_table(
            'opportunity_clusters',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('canonical_opportunity_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('cluster_score', sa.Float(), default=1.0),
            sa.Column('member_count', sa.Integer(), default=1),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['canonical_opportunity_id'], ['opportunities.id'], ondelete='CASCADE')
        )
        op.create_index('ix_cluster_canonical', 'opportunity_clusters', ['canonical_opportunity_id'])

    # ========================================================================
    # OPPORTUNITY CLUSTER MEMBERS TABLE
    # ========================================================================
    if not table_exists('opportunity_cluster_members'):
        op.create_table(
            'opportunity_cluster_members',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('cluster_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('similarity_score', sa.Float(), default=1.0),
            sa.Column('match_type', sa.String(50), default='hash'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['cluster_id'], ['opportunity_clusters.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('opportunity_id')
        )
        op.create_index('ix_cluster_member', 'opportunity_cluster_members', ['cluster_id', 'opportunity_id'])

    # ========================================================================
    # DEADLINE ALERTS TABLE
    # ========================================================================
    if not table_exists('deadline_alerts'):
        op.create_table(
            'deadline_alerts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('alert_type', sa.Enum('D7', 'D3', 'D1', name='alerttype'), nullable=False),
            sa.Column('scheduled_for', sa.DateTime(), nullable=False),
            sa.Column('status', sa.Enum('pending', 'sent', 'failed', 'cancelled', name='alertstatus'), default='pending'),
            sa.Column('sent_at', sa.DateTime(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('channels', postgresql.JSON(), default=[]),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('opportunity_id', 'alert_type', name='uq_deadline_alert')
        )
        op.create_index('ix_deadline_alert_scheduled', 'deadline_alerts', ['scheduled_for', 'status'])

    # ========================================================================
    # SOURCE HEALTH TABLE
    # ========================================================================
    if not table_exists('source_health'):
        op.create_table(
            'source_health',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('requests', sa.Integer(), default=0),
            sa.Column('success_count', sa.Integer(), default=0),
            sa.Column('error_count', sa.Integer(), default=0),
            sa.Column('success_rate', sa.Float(), default=0.0),
            sa.Column('avg_latency_ms', sa.Integer(), default=0),
            sa.Column('max_latency_ms', sa.Integer(), default=0),
            sa.Column('items_found', sa.Integer(), default=0),
            sa.Column('items_kept', sa.Integer(), default=0),
            sa.Column('items_new', sa.Integer(), default=0),
            sa.Column('duplicates_count', sa.Integer(), default=0),
            sa.Column('duplicates_rate', sa.Float(), default=0.0),
            sa.Column('error_types', postgresql.JSON(), default={}),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('health_score', sa.Integer(), default=100),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['source_id'], ['source_configs.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('source_id', 'date', name='uq_source_health_date')
        )
        op.create_index('ix_source_health_date', 'source_health', ['date', 'source_id'])
        op.create_index('ix_source_health_score', 'source_health', ['health_score'])

    # ========================================================================
    # CONTACT FINDER RESULTS TABLE
    # ========================================================================
    if not table_exists('contact_finder_results'):
        op.create_table(
            'contact_finder_results',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('status', sa.String(20), default='pending'),
            sa.Column('contact_email', sa.String(255), nullable=True),
            sa.Column('contact_phone', sa.String(50), nullable=True),
            sa.Column('contact_name', sa.String(255), nullable=True),
            sa.Column('contact_role', sa.String(100), nullable=True),
            sa.Column('evidence_url', sa.String(2000), nullable=True),
            sa.Column('evidence_snippet', sa.Text(), nullable=True),
            sa.Column('evidence_domain', sa.String(255), nullable=True),
            sa.Column('searched_urls', postgresql.JSON(), default=[]),
            sa.Column('search_method', sa.String(50), default='official_first'),
            sa.Column('search_duration_ms', sa.Integer(), nullable=True),
            sa.Column('pages_crawled', sa.Integer(), default=0),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE')
        )
        op.create_index('ix_contact_finder_opportunity', 'contact_finder_results', ['opportunity_id'])
        op.create_index('ix_contact_finder_status', 'contact_finder_results', ['status'])


def downgrade():
    # Drop tables in reverse order (only if they exist)
    if table_exists('contact_finder_results'):
        op.drop_table('contact_finder_results')
    if table_exists('source_health'):
        op.drop_table('source_health')
    if table_exists('deadline_alerts'):
        op.drop_table('deadline_alerts')
    if table_exists('opportunity_cluster_members'):
        op.drop_table('opportunity_cluster_members')
    if table_exists('opportunity_clusters'):
        op.drop_table('opportunity_clusters')
    if table_exists('daily_shortlists'):
        op.drop_table('daily_shortlists')
    if table_exists('opportunity_profile_scores'):
        op.drop_table('opportunity_profile_scores')
    if table_exists('profiles'):
        op.drop_table('profiles')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS alerttype')
    op.execute('DROP TYPE IF EXISTS alertstatus')
