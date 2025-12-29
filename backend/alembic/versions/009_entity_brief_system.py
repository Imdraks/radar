"""Add Entity, Document, Extract, Brief, Contact, CollectionRun models

Revision ID: 009_entity_brief_system
Revises: 008_add_image_url
Create Date: 2025-12-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '009_entity_brief_system'
down_revision = '008_add_image_url'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Helper function to check if enum exists
    def enum_exists(enum_name):
        result = conn.execute(sa.text(
            "SELECT 1 FROM pg_type WHERE typname = :name"
        ), {"name": enum_name})
        return result.scalar() is not None
    
    # Create enums if not exist
    if not enum_exists('entitytype'):
        op.execute("CREATE TYPE entitytype AS ENUM ('PERSON', 'ORGANIZATION', 'TOPIC')")
    
    if not enum_exists('objectivetype'):
        op.execute("CREATE TYPE objectivetype AS ENUM ('SPONSOR', 'BOOKING', 'PRESS', 'VENUE', 'SUPPLIER', 'GRANT')")
    
    if not enum_exists('contacttype'):
        op.execute("CREATE TYPE contacttype AS ENUM ('EMAIL', 'FORM', 'BOOKING', 'PRESS', 'AGENT', 'MANAGEMENT', 'SOCIAL', 'PHONE')")

    # Pre-create ENUM types for use in columns (with create_type=False to prevent auto-creation)
    entitytype_enum = postgresql.ENUM('PERSON', 'ORGANIZATION', 'TOPIC', name='entitytype', create_type=False)
    objectivetype_enum = postgresql.ENUM('SPONSOR', 'BOOKING', 'PRESS', 'VENUE', 'SUPPLIER', 'GRANT', name='objectivetype', create_type=False)
    contacttype_enum = postgresql.ENUM('EMAIL', 'FORM', 'BOOKING', 'PRESS', 'AGENT', 'MANAGEMENT', 'SOCIAL', 'PHONE', name='contacttype', create_type=False)

    # === ENTITIES TABLE ===
    if 'entities' not in existing_tables:
        op.create_table(
            'entities',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False, index=True),
            sa.Column('normalized_name', sa.String(255), nullable=False, index=True),
            sa.Column('entity_type', entitytype_enum, nullable=False, index=True),
            sa.Column('aliases', postgresql.ARRAY(sa.String), server_default='{}'),
            sa.Column('official_urls', postgresql.JSON, server_default='[]'),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('image_url', sa.String(2000), nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_entities_name_type', 'entities', ['normalized_name', 'entity_type'])

    # === DOCUMENTS TABLE ===
    if 'documents' not in existing_tables:
        op.create_table(
            'documents',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('source_config_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('source_name', sa.String(255), nullable=False),
            sa.Column('source_url', sa.String(2000), nullable=True),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('url', sa.String(2000), nullable=True, index=True),
            sa.Column('snippet', sa.Text, nullable=True),
            sa.Column('full_content', sa.Text, nullable=True),
            sa.Column('fingerprint', sa.String(64), unique=True, nullable=False, index=True),
            sa.Column('published_at', sa.DateTime, nullable=True, index=True),
            sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('is_processed', sa.Boolean, server_default='false'),
            sa.Column('processed_at', sa.DateTime, nullable=True),
        )

    # === EXTRACTS TABLE ===
    if 'extracts' not in existing_tables:
        op.create_table(
            'extracts',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('summary', sa.Text, nullable=True),
            sa.Column('contacts_found', postgresql.JSON, server_default='[]'),
            sa.Column('entities_found', postgresql.JSON, server_default='[]'),
            sa.Column('event_signals', postgresql.JSON, server_default='[]'),
            sa.Column('opportunity_type', objectivetype_enum, nullable=True),
            sa.Column('confidence', sa.Float, server_default='0.0'),
            sa.Column('raw_json', postgresql.JSON, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )

    # === CONTACTS TABLE ===
    if 'contacts' not in existing_tables:
        op.create_table(
            'contacts',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('contact_type', contacttype_enum, nullable=False),
            sa.Column('value', sa.String(500), nullable=False),
            sa.Column('label', sa.String(255), nullable=True),
            sa.Column('source_url', sa.String(2000), nullable=True),
            sa.Column('source_name', sa.String(255), nullable=True),
            sa.Column('reliability_score', sa.Integer, server_default='0'),
            sa.Column('is_verified', sa.Boolean, server_default='false'),
            sa.Column('verified_at', sa.DateTime, nullable=True),
            sa.Column('first_seen_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('last_seen_at', sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint('entity_id', 'contact_type', 'value', name='uq_entity_contact'),
        )
        op.create_index('ix_contacts_reliability', 'contacts', ['entity_id', 'reliability_score'])

    # === BRIEFS TABLE ===
    if 'briefs' not in existing_tables:
        op.create_table(
            'briefs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('objective', objectivetype_enum, nullable=False),
            sa.Column('timeframe_days', sa.Integer, server_default='30'),
            sa.Column('overview', sa.Text, nullable=True),
            sa.Column('contacts_ranked', postgresql.JSON, server_default='[]'),
            sa.Column('useful_facts', postgresql.JSON, server_default='[]'),
            sa.Column('timeline', postgresql.JSON, server_default='[]'),
            sa.Column('sources_used', postgresql.JSON, server_default='[]'),
            sa.Column('document_count', sa.Integer, server_default='0'),
            sa.Column('contact_count', sa.Integer, server_default='0'),
            sa.Column('completeness_score', sa.Float, server_default='0.0'),
            sa.Column('generated_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime, nullable=True),
        )

    # === COLLECTION RUNS TABLE ===
    if 'collection_runs' not in existing_tables:
        op.create_table(
            'collection_runs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('objective', objectivetype_enum, nullable=False),
            sa.Column('entities_requested', postgresql.JSON, server_default='[]'),
            sa.Column('secondary_keywords', postgresql.ARRAY(sa.String), server_default='{}'),
            sa.Column('timeframe_days', sa.Integer, server_default='30'),
            sa.Column('require_contact', sa.Boolean, server_default='false'),
            sa.Column('budget_min', sa.Numeric(15, 2), nullable=True),
            sa.Column('budget_max', sa.Numeric(15, 2), nullable=True),
            sa.Column('region', sa.String(100), nullable=True),
            sa.Column('city', sa.String(100), nullable=True),
            sa.Column('status', sa.String(20), server_default='PENDING'),
            sa.Column('started_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('finished_at', sa.DateTime, nullable=True),
            sa.Column('source_count', sa.Integer, server_default='0'),
            sa.Column('sources_success', sa.Integer, server_default='0'),
            sa.Column('sources_failed', sa.Integer, server_default='0'),
            sa.Column('documents_new', sa.Integer, server_default='0'),
            sa.Column('documents_updated', sa.Integer, server_default='0'),
            sa.Column('contacts_found', sa.Integer, server_default='0'),
            sa.Column('error_summary', sa.Text, nullable=True),
            sa.Column('source_runs', postgresql.JSON, server_default='[]'),
        )


def downgrade() -> None:
    op.drop_table('collection_runs')
    op.drop_table('briefs')
    op.drop_table('contacts')
    op.drop_table('extracts')
    op.drop_table('documents')
    op.drop_table('entities')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS contacttype')
    op.execute('DROP TYPE IF EXISTS objectivetype')
    op.execute('DROP TYPE IF EXISTS entitytype')
