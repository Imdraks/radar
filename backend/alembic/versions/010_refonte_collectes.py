"""
Refonte complète du système de collectes
- Nouvelle table collections (source de vérité)
- Table lead_items unifiée (opportunités + candidats dossiers)
- Table source_documents (preuves)
- Table dossiers (packaging IA)
- Table evidence (traçabilité)

Revision ID: 010
Revises: 009
Create Date: 2025-12-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers
revision = '010'
down_revision = '009_entity_brief_system'
branch_labels = None
depends_on = None


def upgrade():
    # ================================================================
    # 1. TABLE COLLECTIONS - Historique des collectes
    # ================================================================
    op.create_table(
        'collections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('type', sa.String(20), nullable=False),  # STANDARD, AI
        sa.Column('status', sa.String(20), nullable=False, default='QUEUED'),  # QUEUED, RUNNING, DONE, FAILED
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('params', JSONB, nullable=True),  # Inputs utilisateur
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('stats', JSONB, nullable=True),  # pages_fetched, results_count, errors_count, tokens_used, cost_estimate
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_collections_type', 'collections', ['type'])
    op.create_index('ix_collections_status', 'collections', ['status'])
    op.create_index('ix_collections_created_at', 'collections', ['created_at'])
    op.create_index('ix_collections_created_by', 'collections', ['created_by'])

    # ================================================================
    # 2. TABLE COLLECTION_LOGS - Logs des collectes
    # ================================================================
    op.create_table(
        'collection_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('level', sa.String(10), nullable=False, default='INFO'),  # DEBUG, INFO, WARNING, ERROR
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('context', JSONB, nullable=True),
    )
    op.create_index('ix_collection_logs_collection_id', 'collection_logs', ['collection_id'])
    op.create_index('ix_collection_logs_ts', 'collection_logs', ['ts'])
    op.create_index('ix_collection_logs_level', 'collection_logs', ['level'])

    # ================================================================
    # 3. TABLE LEAD_ITEMS - Source de vérité unique (Opportunités + Candidats)
    # ================================================================
    op.create_table(
        'lead_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('kind', sa.String(30), nullable=False),  # OPPORTUNITY, DOSSIER_CANDIDATE
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('organization_name', sa.String(300), nullable=True),
        sa.Column('url_primary', sa.String(2000), nullable=True),
        sa.Column('source_id', sa.Integer, sa.ForeignKey('sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_name', sa.String(255), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=True),  # HTML, RSS, EMAIL, API
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deadline_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location_city', sa.String(100), nullable=True),
        sa.Column('location_region', sa.String(100), nullable=True),
        sa.Column('location_country', sa.String(100), nullable=True, default='France'),
        sa.Column('budget_min', sa.Float, nullable=True),
        sa.Column('budget_max', sa.Float, nullable=True),
        sa.Column('budget_currency', sa.String(10), nullable=True, default='EUR'),
        sa.Column('budget_display', sa.String(100), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('contact_url', sa.String(500), nullable=True),
        sa.Column('contact_name', sa.String(200), nullable=True),
        sa.Column('has_contact', sa.Boolean, default=False),
        sa.Column('has_deadline', sa.Boolean, default=False),
        sa.Column('score_base', sa.Integer, nullable=True, default=0),  # 0-100
        sa.Column('score_breakdown', JSONB, nullable=True),  # Détail du scoring
        sa.Column('status', sa.String(30), nullable=False, default='NEW'),  # NEW, QUALIFIED, CONTACTED, WON, LOST, ARCHIVED
        sa.Column('tags', JSONB, nullable=True),  # Array de tags
        sa.Column('assigned_to', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('canonical_hash', sa.String(64), nullable=True, unique=True),  # Pour dédup sans URL
        sa.Column('metadata', JSONB, nullable=True),  # Données additionnelles
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_lead_items_kind', 'lead_items', ['kind'])
    op.create_index('ix_lead_items_status', 'lead_items', ['status'])
    op.create_index('ix_lead_items_score_base', 'lead_items', ['score_base'])
    op.create_index('ix_lead_items_deadline_at', 'lead_items', ['deadline_at'])
    op.create_index('ix_lead_items_created_at', 'lead_items', ['created_at'])
    op.create_index('ix_lead_items_url_primary', 'lead_items', ['url_primary'])
    op.create_index('ix_lead_items_canonical_hash', 'lead_items', ['canonical_hash'])
    op.create_index('ix_lead_items_organization_name', 'lead_items', ['organization_name'])
    op.create_index('ix_lead_items_location_region', 'lead_items', ['location_region'])

    # ================================================================
    # 4. TABLE COLLECTION_RESULTS - Liaison collection <-> lead_items
    # ================================================================
    op.create_table(
        'collection_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_item_id', UUID(as_uuid=True), sa.ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_new', sa.Boolean, default=True),  # Nouveau ou déjà existant (dédup)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_collection_results_collection_id', 'collection_results', ['collection_id'])
    op.create_index('ix_collection_results_lead_item_id', 'collection_results', ['lead_item_id'])
    op.create_unique_constraint('uq_collection_results', 'collection_results', ['collection_id', 'lead_item_id'])

    # ================================================================
    # 5. TABLE SOURCE_DOCUMENTS - Documents bruts (preuves)
    # Note: dossier_id sera ajouté via ALTER TABLE après création de dossiers_v2
    # ================================================================
    op.create_table(
        'source_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('lead_item_id', UUID(as_uuid=True), sa.ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=True),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_id', sa.Integer, sa.ForeignKey('sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('url', sa.String(2000), nullable=True),
        sa.Column('doc_type', sa.String(30), nullable=True),  # HTML, PDF_TEXT, EMAIL_TEXT, WEB_SNAPSHOT_TEXT, WEB_EXTRACT
        sa.Column('raw_html', sa.Text, nullable=True),  # HTML brut
        sa.Column('raw_text', sa.Text, nullable=True),  # Contenu texte extrait
        sa.Column('storage_path', sa.String(500), nullable=True),  # Si stockage fichier
        sa.Column('content_hash', sa.String(64), nullable=True),  # Pour dédup contenu
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),  # content_type, size, etc.
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_source_documents_lead_item_id', 'source_documents', ['lead_item_id'])
    op.create_index('ix_source_documents_collection_id', 'source_documents', ['collection_id'])
    op.create_index('ix_source_documents_doc_type', 'source_documents', ['doc_type'])
    op.create_index('ix_source_documents_url', 'source_documents', ['url'])

    # ================================================================
    # 6. TABLE DOSSIERS - Packaging IA (1:1 avec lead_item)
    # ================================================================
    op.create_table(
        'dossiers_v2',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('lead_item_id', UUID(as_uuid=True), sa.ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('objective', sa.String(30), nullable=False),  # SPONSOR, BOOKING, PRESS, VENUE, SUPPLIER, GRANT
        sa.Column('target_entities', JSONB, nullable=True),  # Array d'entités ciblées
        sa.Column('state', sa.String(20), nullable=False, default='PENDING'),  # PENDING, PROCESSING, READY, FAILED
        sa.Column('sections', JSONB, nullable=True),  # [{title, content, evidence_refs}]
        sa.Column('summary', sa.Text, nullable=True),  # Résumé
        sa.Column('key_findings', JSONB, nullable=True),  # Array de findings
        sa.Column('recommendations', JSONB, nullable=True),  # Array de recommandations
        sa.Column('quality_score', sa.Integer, nullable=True, default=0),  # 0-100
        sa.Column('quality_breakdown', JSONB, nullable=True),  # {completeness, source_quality, relevance}
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('processing_time_ms', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_dossiers_v2_lead_item_id', 'dossiers_v2', ['lead_item_id'])
    op.create_index('ix_dossiers_v2_objective', 'dossiers_v2', ['objective'])
    op.create_index('ix_dossiers_v2_state', 'dossiers_v2', ['state'])
    op.create_index('ix_dossiers_v2_quality_score', 'dossiers_v2', ['quality_score'])

    # Ajouter la FK dossier_id à source_documents maintenant que dossiers_v2 existe
    op.add_column('source_documents', 
        sa.Column('dossier_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_source_documents_dossier', 
        'source_documents', 'dossiers_v2',
        ['dossier_id'], ['id'],
        ondelete='SET NULL'
    )

    # ================================================================
    # 7. TABLE EVIDENCE - Traçabilité des données
    # ================================================================
    op.create_table(
        'evidence',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('lead_item_id', UUID(as_uuid=True), sa.ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=True),
        sa.Column('dossier_id', UUID(as_uuid=True), sa.ForeignKey('dossiers_v2.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source_document_id', UUID(as_uuid=True), sa.ForeignKey('source_documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('field_name', sa.String(100), nullable=False),  # budget_max, contact_email, deadline_at, etc.
        sa.Column('value', sa.Text, nullable=True),  # Valeur extraite
        sa.Column('quote', sa.Text, nullable=True),  # Citation exacte du document
        sa.Column('url', sa.String(2000), nullable=True),  # URL source
        sa.Column('provenance', sa.String(30), nullable=False),  # STANDARD_DOC, WEB_ENRICHED, AI_EXTRACTED, GPT_GROUNDED
        sa.Column('confidence', sa.Float, nullable=True, default=1.0),  # 0.0-1.0
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_evidence_lead_item_id', 'evidence', ['lead_item_id'])
    op.create_index('ix_evidence_dossier_id', 'evidence', ['dossier_id'])
    op.create_index('ix_evidence_field_name', 'evidence', ['field_name'])
    op.create_index('ix_evidence_provenance', 'evidence', ['provenance'])


def downgrade():
    op.drop_table('evidence')
    op.drop_table('dossiers_v2')
    op.drop_table('source_documents')
    op.drop_table('collection_results')
    op.drop_table('lead_items')
    op.drop_table('collection_logs')
    op.drop_table('collections')
