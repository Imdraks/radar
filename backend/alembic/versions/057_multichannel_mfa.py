"""Persistent MFA challenges and additive email/SMS factors; preserve existing TOTP."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '057_multichannel_mfa'
down_revision = '056_full_credit_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('mfa_email_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('mfa_email', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('mfa_sms_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('mfa_phone', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('mfa_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('mfa_totp_last_step', sa.BigInteger(), nullable=True))
    # Invalidate sessions issued before the old SSO/TOTP bypass was closed.
    op.execute('UPDATE users SET mfa_version = 1 WHERE two_factor_enabled = true')
    op.create_table('mfa_challenges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('purpose', sa.String(30), nullable=False),
        sa.Column('method', sa.String(20)), sa.Column('code_hash', sa.String(64)),
        sa.Column('pending_secret', sa.String(255)), sa.Column('destination', sa.String(500)),
        sa.Column('auth_version', sa.Integer(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False), sa.Column('send_count', sa.Integer(), nullable=False),
        sa.Column('last_attempt_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False), sa.Column('last_sent_at', sa.DateTime()),
        sa.Column('expires_at', sa.DateTime(), nullable=False), sa.Column('used_at', sa.DateTime()))
    op.create_index('ix_mfa_challenges_token_hash', 'mfa_challenges', ['token_hash'], unique=True)
    op.create_index('ix_mfa_user_created', 'mfa_challenges', ['user_id', 'created_at'])


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT 1 FROM users WHERE mfa_email_enabled OR mfa_sms_enabled OR mfa_version <> 0 OR two_factor_secret LIKE 'enc:%' OR backup_codes::text LIKE '%v1:%' LIMIT 1")).first():
        raise RuntimeError('Downgrade automatique refusé après activation ou migration de sécurité : préserver les secrets chiffrés, les codes hachés et la révocation des sessions. Suivre la procédure opérateur documentée.')
    op.drop_table('mfa_challenges')
    for column in ['mfa_totp_last_step', 'mfa_version', 'mfa_phone', 'mfa_sms_enabled', 'mfa_email', 'mfa_email_enabled']:
        op.drop_column('users', column)
