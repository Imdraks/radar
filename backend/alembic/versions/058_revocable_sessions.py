"""Track sessions and explicitly authorized browsers. Legacy JWTs require a new login."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '058_revocable_sessions'
down_revision = '057_multichannel_mfa'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('user_sessions', 'trusted_devices'):
        columns = [sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
                   sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
                   sa.Column('auth_version', sa.Integer(), nullable=False),
                   sa.Column('label', sa.String(100), nullable=False),
                   sa.Column('created_at', sa.DateTime(), nullable=False),
                   sa.Column('expires_at', sa.DateTime(), nullable=False),
                   sa.Column('revoked_at', sa.DateTime())]
        if name == 'trusted_devices':
            columns.extend([sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
                            sa.Column('ua_hash', sa.String(64), nullable=False)])
        op.create_table(name, *columns)
        op.create_index('ix_' + name + '_user_id', name, ['user_id'])


def downgrade():
    for name in ('user_sessions', 'trusted_devices'):
        if op.get_bind().execute(sa.text('SELECT 1 FROM ' + name + ' LIMIT 1')).first():
            raise RuntimeError('Downgrade automatique refusé après utilisation des sessions : préserver les révocations. Rotation des clés JWT et procédure opérateur nécessaires.')
    op.drop_table('trusted_devices')
    op.drop_table('user_sessions')
