"""Add dossier system tables

Revision ID: 010_dossier_system
Revises: 009_entity_brief_system
Create Date: 2025-12-25

Adds:
- source_documents: Raw content storage for grounding
- dossiers: Enriched opportunity analysis
- dossier_evidence: Anti-hallucination proof
- web_enrichment_runs: Track enrichment jobs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = '010_dossier_system'
down_revision = '009_entity_brief_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # ========================================================================
    # SOURCE DOCUMENTS
    # ========================================================================
    if 'source_documents' not in existing_tables:
        op.create_table(
            'source_documents',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('opportunity_id', sa.Integer(), 
                      sa.ForeignKey('opportunities.id', ondelete='CASCADE'), 
                      nullable=False, index=True),
            sa.Column('doc_type', sa.String(30), nullable=False, index=True),
            sa.Column('raw_text', sa.Text(), nullable=True),
            sa.Column('raw_html', sa.Text(), nullable=True),
            sa.Column('raw_metadata', sa.JSON(), default=dict),
            sa.Column('source_url', sa.String(2000), nullable=True),
            sa.Column('fetched_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index('ix_source_docs_opp_type', 'source_documents', 
                        ['opportunity_id', 'doc_type'])
    
    # ========================================================================
    # DOSSIERS
    # ========================================================================
    if 'dossiers' not in existing_tables:
        op.create_table(
            'dossiers',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('opportunity_id', sa.Integer(), 
                      sa.ForeignKey('opportunities.id', ondelete='CASCADE'), 
                      nullable=False, unique=True, index=True),
            sa.Column('state', sa.String(20), nullable=False, default='NOT_CREATED', index=True),
            
            # GPT Generated Content
            sa.Column('summary_short', sa.String(500), nullable=True),
            sa.Column('summary_long', sa.Text(), nullable=True),
            sa.Column('key_points', sa.JSON(), default=list),
            sa.Column('action_checklist', sa.JSON(), default=list),
            
            # Extracted Fields
            sa.Column('extracted_fields', sa.JSON(), default=dict),
            
            # Quality & Confidence
            sa.Column('confidence_plus', sa.Integer(), default=0),
            sa.Column('quality_flags', sa.JSON(), default=list),
            sa.Column('missing_fields', sa.JSON(), default=list),
            
            # Source Tracking
            sa.Column('sources_used', sa.JSON(), default=list),
            
            # Final Scoring
            sa.Column('score_final', sa.Integer(), default=0, index=True),
            
            # Processing info
            sa.Column('gpt_model_used', sa.String(50), nullable=True),
            sa.Column('tokens_used', sa.Integer(), default=0),
            sa.Column('processing_time_ms', sa.Integer(), default=0),
            
            # Error tracking
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('retry_count', sa.Integer(), default=0),
            
            # Timestamps
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), 
                      onupdate=sa.func.now()),
            sa.Column('processed_at', sa.DateTime(), nullable=True),
            sa.Column('enriched_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_dossiers_state_score', 'dossiers', ['state', 'score_final'])
    
    # ========================================================================
    # DOSSIER EVIDENCE
    # ========================================================================
    if 'dossier_evidence' not in existing_tables:
        op.create_table(
            'dossier_evidence',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('dossier_id', UUID(as_uuid=True), 
                      sa.ForeignKey('dossiers.id', ondelete='CASCADE'), 
                      nullable=False, index=True),
            sa.Column('field_key', sa.String(50), nullable=False, index=True),
            sa.Column('value', sa.Text(), nullable=True),
            sa.Column('provenance', sa.String(20), nullable=False, default='STANDARD_DOC'),
            sa.Column('evidence_type', sa.String(20), nullable=False),
            sa.Column('evidence_ref', sa.String(2000), nullable=True),
            sa.Column('source_document_id', UUID(as_uuid=True), 
                      sa.ForeignKey('source_documents.id', ondelete='SET NULL'), 
                      nullable=True),
            sa.Column('evidence_snippet', sa.String(500), nullable=True),
            sa.Column('confidence', sa.Integer(), default=50),
            sa.Column('source_url', sa.String(2000), nullable=True),
            sa.Column('retrieved_at', sa.DateTime(), nullable=True),
            sa.Column('retrieval_method', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index('ix_evidence_dossier_field', 'dossier_evidence', 
                        ['dossier_id', 'field_key'])
    
    # ========================================================================
    # WEB ENRICHMENT RUNS
    # ========================================================================
    if 'web_enrichment_runs' not in existing_tables:
        op.create_table(
            'web_enrichment_runs',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('dossier_id', UUID(as_uuid=True), 
                      sa.ForeignKey('dossiers.id', ondelete='CASCADE'), 
                      nullable=False, index=True),
            sa.Column('status', sa.String(20), default='PENDING'),
            sa.Column('target_fields', sa.JSON(), default=list),
            sa.Column('fields_found', sa.JSON(), default=list),
            sa.Column('fields_not_found', sa.JSON(), default=list),
            sa.Column('actors_used', sa.JSON(), default=list),
            sa.Column('urls_consulted', sa.JSON(), default=list),
            sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('duration_ms', sa.Integer(), nullable=True),
            sa.Column('errors', sa.JSON(), default=list),
        )
    
    # ========================================================================
    # ADD score_base to opportunities (rename score -> score_base for clarity)
    # ========================================================================
    # Check if columns already exist
    existing_columns = [col['name'] for col in inspector.get_columns('opportunities')]
    
    if 'score_base' not in existing_columns:
        op.add_column('opportunities', 
                      sa.Column('score_base', sa.Integer(), default=0, index=True))
    if 'score_breakdown_base' not in existing_columns:
        op.add_column('opportunities', 
                      sa.Column('score_breakdown_base', sa.JSON(), default=dict))
    
    # Copy existing score data only if columns were just created
    if 'score_base' not in existing_columns:
        op.execute("UPDATE opportunities SET score_base = score, score_breakdown_base = score_breakdown")


def downgrade() -> None:
    # Remove new columns from opportunities
    op.drop_column('opportunities', 'score_breakdown_base')
    op.drop_column('opportunities', 'score_base')
    
    # Drop tables in reverse order
    op.drop_table('web_enrichment_runs')
    op.drop_table('dossier_evidence')
    op.drop_table('dossiers')
    op.drop_table('source_documents')
