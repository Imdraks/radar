"""Add billing tables for quotes and invoices

Revision ID: 010_billing
Revises: 009_entity_brief_system
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = '010_billing'
down_revision = '009_entity_brief_system'
branch_labels = None
# This branch references workspaces, introduced by the inbox branch.
# Preserve revision IDs/parents for already-stamped databases.
depends_on = '020_workspace_inbox'


def upgrade():
    # Create enums
    quote_status_enum = ENUM(
        'DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'INVOICED',
        name='quotestatus',
        create_type=False
    )
    invoice_status_enum = ENUM(
        'DRAFT', 'SENT', 'PAID', 'PARTIAL', 'OVERDUE', 'CANCELLED',
        name='invoicestatus',
        create_type=False
    )
    payment_method_enum = ENUM(
        'BANK_TRANSFER', 'CHECK', 'CASH', 'CARD', 'OTHER',
        name='paymentmethod',
        create_type=False
    )
    
    # Create enums in database
    op.execute("CREATE TYPE quotestatus AS ENUM ('DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'INVOICED')")
    op.execute("CREATE TYPE invoicestatus AS ENUM ('DRAFT', 'SENT', 'PAID', 'PARTIAL', 'OVERDUE', 'CANCELLED')")
    op.execute("CREATE TYPE paymentmethod AS ENUM ('BANK_TRANSFER', 'CHECK', 'CASH', 'CARD', 'OTHER')")
    
    # Create billing_clients table
    op.create_table(
        'billing_clients',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), default='France'),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('siret', sa.String(20), nullable=True),
        sa.Column('vat_number', sa.String(30), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create quotes table
    op.create_table(
        'quotes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('reference', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('billing_clients.id'), nullable=True),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id'), nullable=True),
        sa.Column('status', quote_status_enum, nullable=False, server_default='DRAFT'),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('validity_date', sa.Date(), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), default=0),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=20.00),
        sa.Column('tax_amount', sa.Numeric(12, 2), default=0),
        sa.Column('total', sa.Numeric(12, 2), default=0),
        sa.Column('discount_percent', sa.Numeric(5, 2), default=0),
        sa.Column('discount_amount', sa.Numeric(12, 2), default=0),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('invoice_id', sa.Integer(), nullable=True),  # FK added later
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('reference', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('billing_clients.id'), nullable=True),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id'), nullable=True),
        sa.Column('source_quote_id', sa.Integer(), sa.ForeignKey('quotes.id'), nullable=True),
        sa.Column('status', invoice_status_enum, nullable=False, server_default='DRAFT'),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('paid_date', sa.Date(), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), default=0),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=20.00),
        sa.Column('tax_amount', sa.Numeric(12, 2), default=0),
        sa.Column('total', sa.Numeric(12, 2), default=0),
        sa.Column('amount_paid', sa.Numeric(12, 2), default=0),
        sa.Column('payment_method', payment_method_enum, nullable=True),
        sa.Column('discount_percent', sa.Numeric(5, 2), default=0),
        sa.Column('discount_amount', sa.Numeric(12, 2), default=0),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Add FK from quotes.invoice_id to invoices.id
    op.create_foreign_key(
        'fk_quotes_invoice_id',
        'quotes', 'invoices',
        ['invoice_id'], ['id']
    )
    
    # Create quote_items table
    op.create_table(
        'quote_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('quote_id', sa.Integer(), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer(), default=0),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), default=1),
        sa.Column('unit', sa.String(50), default='unité'),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('line_total', sa.Numeric(12, 2), nullable=False),
    )
    
    # Create invoice_items table
    op.create_table(
        'invoice_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer(), default=0),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), default=1),
        sa.Column('unit', sa.String(50), default='unité'),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('line_total', sa.Numeric(12, 2), nullable=False),
    )


def downgrade():
    op.drop_table('invoice_items')
    op.drop_table('quote_items')
    op.drop_constraint('fk_quotes_invoice_id', 'quotes', type_='foreignkey')
    op.drop_table('invoices')
    op.drop_table('quotes')
    op.drop_table('billing_clients')
    
    op.execute('DROP TYPE IF EXISTS paymentmethod')
    op.execute('DROP TYPE IF EXISTS invoicestatus')
    op.execute('DROP TYPE IF EXISTS quotestatus')
