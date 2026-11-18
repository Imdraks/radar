"""Optional account photo; original SSO image URL is retained."""
from alembic import op
import sqlalchemy as sa

revision = '059_profile_avatar'
down_revision = '058_revocable_sessions'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('avatar_image', sa.LargeBinary(), nullable=True))


def downgrade():
    # Preserve uploaded user photos: export/remove them explicitly before rollback.
    if op.get_bind().execute(sa.text('SELECT 1 FROM users WHERE avatar_image IS NOT NULL LIMIT 1')).first():
        raise RuntimeError('Exporter les photos personnalisées avant de retirer avatar_image ; aucune suppression automatique.')
    op.drop_column('users', 'avatar_image')
