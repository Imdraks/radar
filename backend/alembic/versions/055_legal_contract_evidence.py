"""Preserve versioned B2B texts and explicit acceptance; never fabricate historical consent."""

from alembic import op
import sqlalchemy as sa

revision = "055_legal_contract_evidence"
down_revision = "054_invoice_legal_details"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "legal_bundles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(80), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("publisher", sa.JSON(), nullable=False),
        sa.Column("documents", sa.JSON(), nullable=False),
        sa.Column("review_reference", sa.String(300), nullable=False),
        sa.Column(
            "published_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column(
            "published_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "legal_acceptances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "bundle_id", sa.Integer(), sa.ForeignKey("legal_bundles.id"), nullable=False
        ),
        sa.Column(
            "accepted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("representative", sa.JSON(), nullable=False),
        sa.Column("workspace_name", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("commercial_reference", sa.String(200), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "accepted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "bundle_id",
            "plan",
            "commercial_reference",
            name="uq_legal_acceptance_offer",
        ),
    )
    op.create_index(
        "ix_legal_acceptances_workspace_id", "legal_acceptances", ["workspace_id"]
    )
    op.add_column(
        "subscription_requests",
        sa.Column(
            "contract_acceptance_id",
            sa.Integer(),
            sa.ForeignKey("legal_acceptances.id"),
        ),
    )


def downgrade():
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT 1 FROM legal_bundles LIMIT 1")).first():
        raise RuntimeError(
            "Archive published legal texts and acceptance evidence before downgrade"
        )
    op.drop_column("subscription_requests", "contract_acceptance_id")
    op.drop_table("legal_acceptances")
    op.drop_table("legal_bundles")
