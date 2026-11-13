"""Link agency events and Discovery artists to existing production projects."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "047_production_events"
down_revision = "046_product_subscriptions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("production_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("venue", sa.String(500)),
        sa.Column("starts_at", sa.DateTime, nullable=False),
        sa.Column("ends_at", sa.DateTime, nullable=False),
        sa.Column("forecast_budget", sa.Numeric(14,2)),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()))
    op.create_index("ix_production_events_workspace_id", "production_events", ["workspace_id"])
    op.create_table("production_event_artists",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_id", sa.Integer, sa.ForeignKey("production_events.id"), nullable=False),
        sa.Column("artist_id", UUID(as_uuid=True), sa.ForeignKey("discovery_artists.id"), nullable=False),
        sa.UniqueConstraint("event_id", "artist_id"))
    op.create_table("production_event_expenses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_id", sa.Integer, sa.ForeignKey("production_events.id"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(14,2), nullable=False))
    op.create_index("ix_production_event_expenses_event_id", "production_event_expenses", ["event_id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM production_events)")).scalar():
        raise RuntimeError("Events exist; archive data and plan a manual rollback without deleting production data")
    for table in ("production_event_expenses", "production_event_artists", "production_events"):
        op.drop_table(table)
