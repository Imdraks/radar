"""Workspace production templates and version-bound external reviews."""

from alembic import op
import sqlalchemy as sa

revision = "066_production_tools"
down_revision = "065_workspace_deletion"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "production_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_production_templates_workspace_id", "production_templates", ["workspace_id"]
    )
    op.create_table(
        "deliverable_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "deliverable_id",
            sa.Integer(),
            sa.ForeignKey("deliverables.id"),
            nullable=False,
        ),
        sa.Column(
            "approval_id", sa.Integer(), sa.ForeignKey("approvals.id"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reviewer_name", sa.String(200)),
        sa.Column("feedback", sa.Text()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime()),
    )
    op.create_index(
        "ix_deliverable_reviews_workspace_id", "deliverable_reviews", ["workspace_id"]
    )
    op.create_index(
        "ix_deliverable_reviews_deliverable_id",
        "deliverable_reviews",
        ["deliverable_id"],
    )


def downgrade():
    for table in ["production_templates", "deliverable_reviews"]:
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError(
                "Exporter et traiter les modèles et validations avant un rollback destructif."
            )
    op.drop_table("deliverable_reviews")
    op.drop_table("production_templates")
