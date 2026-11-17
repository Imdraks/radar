"""Full credit notes preserve source invoices and their original payment history."""

from alembic import op
import sqlalchemy as sa

revision = "056_full_credit_notes"
down_revision = "055_legal_contract_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("credited_at", sa.DateTime(), nullable=True))
    op.create_table(
        "credit_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("reference", sa.String(50), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("workspace_id", "reference", name="uq_credit_reference"),
        sa.UniqueConstraint(
            "workspace_id", "idempotency_key", name="uq_credit_idempotency"
        ),
    )
    op.create_index("ix_credit_notes_workspace_id", "credit_notes", ["workspace_id"])


def downgrade():
    conn = op.get_bind()
    if (
        conn.execute(sa.text("SELECT 1 FROM credit_notes LIMIT 1")).first()
        or conn.execute(
            sa.text("SELECT 1 FROM invoices WHERE credited_at IS NOT NULL LIMIT 1")
        ).first()
    ):
        raise RuntimeError(
            "Archive credit notes and their invoice links before downgrade"
        )
    op.drop_table("credit_notes")
    op.drop_column("invoices", "credited_at")
