"""Separate modern tag associations from the legacy tag dictionary without deleting either."""
from alembic import op
import sqlalchemy as sa
revision = "048_tag_associations"
down_revision = "047_production_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("custom_opportunity_tags",
        sa.Column("opportunity_id", sa.Integer, sa.ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()))
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("opportunity_tags")}
    if {"opportunity_id", "tag_id"} <= columns:
        op.execute("""INSERT INTO custom_opportunity_tags (opportunity_id, tag_id, created_at)
            SELECT old.opportunity_id, old.tag_id, old.created_at FROM opportunity_tags old
            JOIN opportunities o ON o.id=old.opportunity_id JOIN tags t ON t.id=old.tag_id
            ON CONFLICT DO NOTHING""")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM custom_opportunity_tags)")).scalar():
        raise RuntimeError("Tag associations exist; reconcile and archive before a manual rollback")
    op.drop_table("custom_opportunity_tags")
