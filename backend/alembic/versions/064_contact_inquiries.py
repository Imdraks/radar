"""Persist public contact requests and their first-open acknowledgements."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "064_contact_inquiries"
down_revision = "063_collaborator_entry"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contact_inquiries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("privacy_notice_version", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("opened_at", sa.DateTime()),
        sa.Column(
            "opened_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("acknowledgement_status", sa.String(20), nullable=False),
        sa.Column("acknowledgement_queued_at", sa.DateTime()),
        sa.Column("acknowledgement_sent_at", sa.DateTime()),
        sa.Column("acknowledgement_error", sa.String(50)),
    )
    op.create_index(
        "ix_contact_inquiry_status_created",
        "contact_inquiries",
        ["status", "created_at"],
    )


def downgrade():
    if (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM contact_inquiries LIMIT 1"))
        .first()
    ):
        raise RuntimeError(
            "Conserver et traiter explicitement les demandes de contact avant rollback ; aucune suppression automatique."
        )
    op.drop_table("contact_inquiries")
