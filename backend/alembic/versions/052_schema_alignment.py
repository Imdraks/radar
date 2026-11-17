"""Add mapped fields omitted from historical migrations without guessing ownership."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "052_schema_alignment"
down_revision = "051_invoice_issuance"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "brief_id" not in {
        c["name"] for c in sa.inspect(bind).get_columns("collection_runs")
    }:
        op.add_column(
            "collection_runs", sa.Column("brief_id", UUID(as_uuid=True), nullable=True)
        )
        op.create_foreign_key(
            "fk_collection_runs_brief",
            "collection_runs",
            "briefs",
            ["brief_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "is_internal" not in {
        c["name"] for c in sa.inspect(bind).get_columns("comments")
    }:
        # Preserve privacy of historical comments; never make them public by default.
        op.add_column(
            "comments",
            sa.Column(
                "is_internal", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )


def downgrade():
    bind = op.get_bind()
    if (
        bind.execute(
            sa.text("SELECT 1 FROM collection_runs WHERE brief_id IS NOT NULL LIMIT 1")
        ).first()
        or bind.execute(
            sa.text("SELECT 1 FROM comments WHERE is_internal IS FALSE LIMIT 1")
        ).first()
    ):
        raise RuntimeError(
            "Archive collection links and comment visibility before downgrade"
        )
    # Additive compatibility fields can predate this revision in manually repaired installations.
    # Retain them on downgrade to avoid deleting fields owned by an older deployed version.
