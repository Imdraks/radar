"""Store explicit service/payment/customer information; never infer past invoice terms."""

from alembic import op
import sqlalchemy as sa

revision = "054_invoice_legal_details"
down_revision = "053_privacy_requests"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("legal_details", sa.JSON(), nullable=True))


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text("SELECT 1 FROM invoices WHERE legal_details IS NOT NULL LIMIT 1")
        )
        .first()
    ):
        raise RuntimeError("Archive invoice legal details before downgrade")
    op.drop_column("invoices", "legal_details")
