"""Account-bound WebAuthn credentials and one-use verification challenges."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "061_passkeys"
down_revision = "060_client_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "passkey_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime()),
        sa.Column("revoked_at", sa.DateTime()),
    )
    op.create_index(
        "ix_passkey_credentials_user_id", "passkey_credentials", ["user_id"]
    )
    op.create_table(
        "passkey_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("challenge", sa.LargeBinary(), nullable=False),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column("parent_token_hash", sa.String(64)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime()),
    )
    op.create_index(
        "ix_passkey_challenge_user_created",
        "passkey_challenges",
        ["user_id", "created_at"],
    )


def downgrade():
    if (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM passkey_credentials LIMIT 1"))
        .first()
    ):
        raise RuntimeError(
            "Exporter et traiter explicitement les clés d’accès avant rollback ; aucune suppression de facteur automatique."
        )
    op.drop_table("passkey_challenges")
    op.drop_table("passkey_credentials")
