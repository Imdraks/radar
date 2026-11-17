"""Official plans, legacy snapshot and audited commercial requests.

No production migration is executed by this change.
"""
from alembic import op
import sqlalchemy as sa

revision = "046_product_subscriptions"
down_revision = "045_artist_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("subscription_legacy_snapshot",
        sa.Column("workspace_id", sa.Integer, primary_key=True),
        sa.Column("previous_plan", sa.String(20), nullable=False),
        sa.Column("migrated_plan", sa.String(20), nullable=False))
    # Existing business rights are grandfathered; no invoice or charge is created.
    op.execute("""
        INSERT INTO subscription_legacy_snapshot (workspace_id, previous_plan, migrated_plan)
        SELECT id, plan, CASE
            WHEN plan = 'premium' OR COALESCE(addons::jsonb, '[]'::jsonb) ? 'radar_business'
              OR COALESCE(enabled_packs::jsonb, '[]'::jsonb) ?| ARRAY['clients','leads'] THEN 'business'
            WHEN plan = 'standard' THEN 'premium'
            ELSE 'core' END
        FROM workspaces WHERE plan IN ('mini', 'standard', 'premium')
    """)
    op.execute("UPDATE workspaces w SET plan = s.migrated_plan FROM subscription_legacy_snapshot s WHERE w.id=s.workspace_id")
    op.alter_column("workspaces", "max_seats", server_default="3")
    op.alter_column("workspaces", "plan", server_default="core")
    op.alter_column("workspaces", "enabled_packs", server_default=sa.text("'[\"core\"]'::json"))
    op.create_table("subscription_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("requested_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("requested_value", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("decided_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("decided_at", sa.DateTime),
        sa.Column("authorization_reference", sa.Text),
        sa.Column("previous_plan", sa.String(20)))
    op.create_index("ix_subscription_requests_workspace_id", "subscription_requests", ["workspace_id"])
    op.create_index("ix_subscription_pending_request", "subscription_requests", ["workspace_id", "kind", "requested_value"],
                    unique=True, postgresql_where=sa.text("status = 'pending'"))


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT EXISTS (SELECT 1 FROM subscription_requests)")).scalar():
        raise RuntimeError("Archive subscription requests and authorization evidence before a manual rollback")
    if connection.execute(sa.text("SELECT EXISTS (SELECT 1 FROM workspaces w JOIN subscription_legacy_snapshot s ON w.id=s.workspace_id WHERE w.plan <> s.migrated_plan)")).scalar():
        raise RuntimeError("Plans changed since migration; manual reconciliation required")
    op.execute("UPDATE workspaces w SET plan = s.previous_plan FROM subscription_legacy_snapshot s WHERE w.id=s.workspace_id")
    op.alter_column("workspaces", "max_seats", server_default="10")
    op.alter_column("workspaces", "plan", server_default="standard")
    op.alter_column("workspaces", "enabled_packs", server_default=sa.text("'[\"core\",\"clients\",\"leads\",\"talents\"]'::json"))
    op.drop_table("subscription_requests")
    op.drop_table("subscription_legacy_snapshot")
