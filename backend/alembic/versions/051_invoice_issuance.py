"""Freeze issuer and customer identities on invoice issuance; preserve historical originals."""

from alembic import op
import sqlalchemy as sa

revision = "051_invoice_issuance"
down_revision = "050_collection_ownership"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("issued_at", sa.DateTime(), nullable=True))
    op.add_column("invoices", sa.Column("issued_snapshot", sa.JSON(), nullable=True))


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM invoices WHERE issued_at IS NOT NULL OR issued_snapshot IS NOT NULL LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError("Issued invoice evidence must be archived before downgrade")
    op.drop_column("invoices", "issued_snapshot")
    op.drop_column("invoices", "issued_at")
