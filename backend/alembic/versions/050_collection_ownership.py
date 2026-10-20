"""Scope legacy collection runs without guessing their organization."""
from alembic import op
import sqlalchemy as sa

revision = '050_collection_ownership'
down_revision = '049_billing_numbering'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('collection_runs', sa.Column('workspace_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_collection_runs_workspace_id', 'collection_runs', 'workspaces', ['workspace_id'], ['id'])
    op.create_index('ix_collection_runs_workspace_id', 'collection_runs', ['workspace_id'])
    # No arbitrary default: historical unassigned runs stay intact but hidden from tenant APIs.


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM collection_runs WHERE workspace_id IS NOT NULL)')).scalar():
        raise RuntimeError('Archive collection ownership before manual rollback; removing it would reopen cross-tenant access')
    op.drop_index('ix_collection_runs_workspace_id', table_name='collection_runs')
    op.drop_constraint('fk_collection_runs_workspace_id', 'collection_runs', type_='foreignkey')
    op.drop_column('collection_runs', 'workspace_id')
