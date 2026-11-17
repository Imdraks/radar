"""Number documents per organization and preserve numbering counters."""
from alembic import op
import sqlalchemy as sa
revision = "049_billing_numbering"
down_revision = "048_tag_associations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("billing_counters",
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("year", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(10), primary_key=True),
        sa.Column("last_number", sa.Integer, nullable=False))
    for table, kind in (("quotes", "DEV"), ("invoices", "FAC")):
        # Seed from existing references without renumbering a single document.
        op.execute(sa.text(f"""INSERT INTO billing_counters (workspace_id, year, kind, last_number)
          SELECT workspace_id, split_part(reference,'-',2)::integer, '{kind}',
                 max(split_part(reference,'-',3)::integer)
          FROM {table} WHERE reference ~ '^{kind}-[0-9]{{4}}-[0-9]+$'
          GROUP BY workspace_id, split_part(reference,'-',2)::integer"""))
        inspector = sa.inspect(op.get_bind())
        for constraint in inspector.get_unique_constraints(table):
            if constraint['column_names'] == ['reference']:
                op.drop_constraint(constraint['name'], table, type_='unique')
        for index in sa.inspect(op.get_bind()).get_indexes(table):
            if index.get('unique') and index['column_names'] == ['reference'] and not index.get('duplicates_constraint'):
                op.drop_index(index['name'], table_name=table)
                op.create_index(index['name'], table, ['reference'], unique=False)
        op.create_unique_constraint(f"uq_{table}_workspace_reference", table, ["workspace_id", "reference"])


def downgrade():
    for table in ("quotes", "invoices"):
        if op.get_bind().execute(sa.text(f'SELECT EXISTS (SELECT reference FROM {table} GROUP BY reference HAVING count(*) > 1)')).scalar():
            raise RuntimeError("Cross-company reference duplicates are valid now; manual rollback required without renumbering invoices")
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM billing_counters)')).scalar():
        raise RuntimeError("Preserve numbering counters in an archive before a manual rollback")
    for table in ("quotes", "invoices"):
        op.drop_constraint(f"uq_{table}_workspace_reference", table, type_="unique")
        op.create_unique_constraint(f"uq_{table}_reference", table, ["reference"])
    op.drop_table("billing_counters")
