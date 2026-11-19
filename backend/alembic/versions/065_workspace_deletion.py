"""Logical workspace removal, preserving accounts and business/contract records."""

from alembic import op
import sqlalchemy as sa

revision = "065_workspace_deletion"
down_revision = "064_contact_inquiries"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workspaces", sa.Column("deleted_at", sa.DateTime()))
    op.add_column("workspaces", sa.Column("deleted_by", sa.Integer()))


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text("SELECT 1 FROM workspaces WHERE deleted_at IS NOT NULL LIMIT 1")
        )
        .first()
    ):
        raise RuntimeError(
            "Traiter explicitement les espaces supprimés avant rollback ; leur réactivation automatique est refusée."
        )
    op.drop_column("workspaces", "deleted_by")
    op.drop_column("workspaces", "deleted_at")
