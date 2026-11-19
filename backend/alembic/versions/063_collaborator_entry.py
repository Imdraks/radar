"""Explicit collaborator entry preference; no workspace membership or role change."""

from alembic import op
import sqlalchemy as sa

revision = "063_collaborator_entry"
down_revision = "062_platform_sales"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "is_collaborator", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade():
    if (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM users WHERE is_collaborator LIMIT 1"))
        .first()
    ):
        raise RuntimeError(
            "Conserver les préférences des comptes collaborateurs avant rollback."
        )
    op.drop_column("users", "is_collaborator")
