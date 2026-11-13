"""Record authenticated privacy and switching requests without deleting customer data."""

from alembic import op
import sqlalchemy as sa

revision = "053_privacy_requests"
down_revision = "052_schema_alignment"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="received"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("response_due_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("audit_log", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_privacy_requests_user_id", "privacy_requests", ["user_id"])
    op.create_index(
        "ix_privacy_requests_workspace_id", "privacy_requests", ["workspace_id"]
    )


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM privacy_requests LIMIT 1")).first():
        raise RuntimeError(
            "Archive rights requests and their evidence before downgrade"
        )
    op.drop_table("privacy_requests")
