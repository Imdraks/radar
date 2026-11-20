"""Bind browser sessions to a public device key without changing native sessions."""

from alembic import op
import sqlalchemy as sa

revision = "067_browser_key_binding"
down_revision = "066_production_tools"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_sessions", sa.Column("browser_public_key", sa.JSON(), nullable=True)
    )


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM user_sessions WHERE browser_public_key IS NOT NULL AND browser_public_key::text <> 'null' AND revoked_at IS NULL LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError(
            "Révoquer explicitement les sessions liées avant de retirer leur protection anti-rejeu."
        )
    op.drop_column("user_sessions", "browser_public_key")
