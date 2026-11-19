"""Platform quotes and manually reviewed external customer contracts."""

from alembic import op
import sqlalchemy as sa

revision = "062_platform_sales"
down_revision = "061_passkeys"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "platform_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("subscription_requests.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("issuer", sa.JSON(), nullable=False),
        sa.Column("buyer", sa.JSON(), nullable=False),
        sa.Column("lines", sa.JSON(), nullable=False),
        sa.Column("total_ht", sa.Numeric(16, 2), nullable=False),
        sa.Column("total_tax", sa.Numeric(16, 2), nullable=False),
        sa.Column("total_ttc", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(3000), nullable=False),
        sa.Column(
            "created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("issued_at", sa.DateTime()),
        sa.Column("content_hash", sa.String(64)),
    )
    op.create_index(
        "ix_platform_quotes_workspace_id", "platform_quotes", ["workspace_id"]
    )
    op.create_table(
        "external_client_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("subscription_requests.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "quote_id",
            sa.Integer(),
            sa.ForeignKey("platform_quotes.id", ondelete="SET NULL"),
        ),
        sa.Column("plan", sa.String(20)),
        sa.Column("reference", sa.String(200), nullable=False),
        sa.Column("signer", sa.String(255), nullable=False),
        sa.Column("signed_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("document", sa.LargeBinary(), nullable=False),
        sa.Column("document_hash", sa.String(64), nullable=False),
        sa.Column(
            "uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("review_reference", sa.String(1000)),
    )
    op.create_index(
        "ix_external_client_contracts_workspace_id",
        "external_client_contracts",
        ["workspace_id"],
    )
    op.add_column(
        "subscription_requests",
        sa.Column(
            "external_contract_id",
            sa.Integer(),
            sa.ForeignKey("external_client_contracts.id", ondelete="SET NULL"),
        ),
    )


def downgrade():
    db = op.get_bind()
    if (
        db.execute(sa.text("SELECT 1 FROM platform_quotes LIMIT 1")).first()
        or db.execute(
            sa.text("SELECT 1 FROM external_client_contracts LIMIT 1")
        ).first()
    ):
        raise RuntimeError(
            "Exporter et traiter explicitement les documents commerciaux avant rollback ; aucune suppression automatique."
        )
    op.drop_column("subscription_requests", "external_contract_id")
    op.drop_table("external_client_contracts")
    op.drop_table("platform_quotes")
