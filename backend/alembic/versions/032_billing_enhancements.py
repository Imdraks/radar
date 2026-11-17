"""Billing enhancements: workspace emitter info + quote/invoice Drive fields

Revision ID: 032_billing_enhancements
Revises: 031_subscription_plans
Create Date: 2026-01-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '032_billing_enhancements'
down_revision = '031_subscription_plans'
branch_labels = None
depends_on = '010_billing'


def add_missing_column(table, column):
    # 020 already creates some of these workspace columns. Never overwrite them.
    if column.name not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    # =========== WORKSPACE: Emitter/Billing info ===========
    add_missing_column('workspaces', sa.Column('devis_template_doc_id', sa.String(255), nullable=True))
    add_missing_column('workspaces', sa.Column('facture_template_doc_id', sa.String(255), nullable=True))
    add_missing_column('workspaces', sa.Column('legal_name', sa.String(255), nullable=True))
    add_missing_column('workspaces', sa.Column('legal_address', sa.String(500), nullable=True))
    add_missing_column('workspaces', sa.Column('legal_city', sa.String(100), nullable=True))
    add_missing_column('workspaces', sa.Column('legal_postal_code', sa.String(20), nullable=True))
    add_missing_column('workspaces', sa.Column('legal_country', sa.String(100), nullable=True, server_default='France'))
    add_missing_column('workspaces', sa.Column('legal_phone', sa.String(50), nullable=True))
    add_missing_column('workspaces', sa.Column('legal_email', sa.String(255), nullable=True))
    add_missing_column('workspaces', sa.Column('siret', sa.String(20), nullable=True))
    add_missing_column('workspaces', sa.Column('vat_number', sa.String(30), nullable=True))
    add_missing_column('workspaces', sa.Column('logo_drive_file_id', sa.String(255), nullable=True))
    add_missing_column('workspaces', sa.Column('payment_info', JSON, nullable=True))
    
    # =========== QUOTES: Drive integration + audit ===========
    add_missing_column('quotes', sa.Column('drive_doc_id', sa.String(255), nullable=True))
    add_missing_column('quotes', sa.Column('drive_pdf_id', sa.String(255), nullable=True))
    add_missing_column('quotes', sa.Column('drive_web_view_link', sa.String(500), nullable=True))
    add_missing_column('quotes', sa.Column('drive_folder_id', sa.String(255), nullable=True))
    add_missing_column('quotes', sa.Column('audit_log', JSON, nullable=True, server_default='[]'))
    add_missing_column('quotes', sa.Column('sent_at', sa.DateTime(), nullable=True))
    add_missing_column('quotes', sa.Column('sent_to_email', sa.String(255), nullable=True))
    
    # =========== INVOICES: Drive integration + audit ===========
    add_missing_column('invoices', sa.Column('drive_doc_id', sa.String(255), nullable=True))
    add_missing_column('invoices', sa.Column('drive_pdf_id', sa.String(255), nullable=True))
    add_missing_column('invoices', sa.Column('drive_web_view_link', sa.String(500), nullable=True))
    add_missing_column('invoices', sa.Column('drive_folder_id', sa.String(255), nullable=True))
    add_missing_column('invoices', sa.Column('audit_log', JSON, nullable=True, server_default='[]'))
    add_missing_column('invoices', sa.Column('sent_at', sa.DateTime(), nullable=True))
    add_missing_column('invoices', sa.Column('sent_to_email', sa.String(255), nullable=True))


def downgrade() -> None:
    raise RuntimeError(
        "032 shares columns with 020. Automatic downgrade would destroy existing billing data; "
        "use a verified backup and a reviewed restoration plan."
    )
