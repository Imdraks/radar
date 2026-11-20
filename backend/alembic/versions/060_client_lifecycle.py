"""Platform client suspension and first-login account provisioning."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "060_client_lifecycle"
down_revision = "059_profile_avatar"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workspaces",
        sa.Column(
            "is_suspended", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("workspaces", sa.Column("suspended_at", sa.DateTime(), nullable=True))
    op.add_column(
        "workspaces", sa.Column("suspension_reason", sa.String(1000), nullable=True)
    )
    op.add_column("workspaces", sa.Column("suspended_by", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("temporary_password_expires_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "security_setup_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "client_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("error_code", sa.String(80)),
    )
    op.create_index(
        "ix_client_invitation_workspace_created",
        "client_invitations",
        ["workspace_id", "created_at"],
    )


def downgrade():
    db = op.get_bind()
    if (
        db.execute(
            sa.text("SELECT 1 FROM workspaces WHERE is_suspended LIMIT 1")
        ).first()
        or db.execute(
            sa.text(
                "SELECT 1 FROM users WHERE must_change_password OR security_setup_pending LIMIT 1"
            )
        ).first()
    ):
        raise RuntimeError(
            "Réactiver les espaces et terminer les parcours de sécurité avant le rollback ; aucun contrôle ne sera supprimé silencieusement."
        )
    if db.execute(sa.text("SELECT 1 FROM client_invitations LIMIT 1")).first():
        raise RuntimeError(
            "Exporter et traiter explicitement l’historique des invitations avant le rollback ; aucune suppression automatique."
        )
    op.drop_table("client_invitations")
    for name in [
        "security_setup_pending",
        "temporary_password_expires_at",
        "must_change_password",
    ]:
        op.drop_column("users", name)
    for name in ["suspended_by", "suspension_reason", "suspended_at", "is_suspended"]:
        op.drop_column("workspaces", name)
