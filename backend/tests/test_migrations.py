"""New migrations execute against a minimal pre-change PostgreSQL schema."""
import importlib.util
from pathlib import Path
from uuid import uuid4
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text


def load_migration(name):
    path = Path(__file__).parents[1] / 'alembic' / 'versions' / name
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_subscription_migration_preserves_seats_and_is_reversible(engine):
    with engine.connect() as connection, connection.begin():
        schema = 'migration_' + uuid4().hex
        connection.execute(text(f'CREATE SCHEMA {schema}'))
        connection.execute(text(f'SET LOCAL search_path TO {schema}'))
        connection.execute(text('CREATE TABLE users (id integer primary key)'))
        connection.execute(text('CREATE TABLE workspaces (id integer primary key, plan varchar(20) not null, enabled_packs json, addons json, max_seats integer)'))
        connection.execute(text("""INSERT INTO workspaces VALUES
            (1,'mini','["core"]','[]',3), (2,'standard','["core","talents"]','[]',10),
            (3,'premium','["core"]','[]',42), (4,'mini','["core","clients"]','[]',7)"""))
        migration = load_migration('046_product_subscriptions.py')
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            rows = connection.execute(text('SELECT plan,max_seats FROM workspaces ORDER BY id')).all()
            assert rows == [('core',3),('premium',10),('business',42),('business',7)]
            migration.downgrade()
            assert connection.execute(text('SELECT plan FROM workspaces ORDER BY id')).scalars().all() == ['mini','standard','premium','mini']
        connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_event_migration_upgrade_downgrade(engine):
    with engine.connect() as connection, connection.begin():
        schema = 'migration_' + uuid4().hex
        connection.execute(text(f'CREATE SCHEMA {schema}'))
        connection.execute(text(f'SET LOCAL search_path TO {schema}'))
        for table, keytype in [('workspaces','integer'),('projects','integer'),('discovery_artists','uuid')]:
            connection.execute(text(f'CREATE TABLE {table} (id {keytype} primary key)'))
        migration = load_migration('047_production_events.py')
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT to_regclass('production_events')")).scalar()
            migration.downgrade()
            assert connection.execute(text("SELECT to_regclass('production_events')")).scalar() is None
        connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_billing_migration_seeds_numbers_without_renumbering(engine):
    from app.api.billing import generate_quote_reference
    from sqlalchemy.orm import Session
    from datetime import datetime
    with engine.connect() as connection, connection.begin():
        schema = 'migration_' + uuid4().hex
        connection.execute(text(f'CREATE SCHEMA {schema}'))
        connection.execute(text(f'SET LOCAL search_path TO {schema}'))
        connection.execute(text('CREATE TABLE workspaces (id integer primary key)'))
        connection.execute(text('INSERT INTO workspaces VALUES (1),(2)'))
        for table in ['quotes','invoices']:
            connection.execute(text(f'CREATE TABLE {table} (id integer primary key, workspace_id integer NOT NULL, reference varchar(50) UNIQUE NOT NULL)'))
        year = datetime.utcnow().year
        reference = f'DEV-{year}-0012'
        connection.execute(text('INSERT INTO quotes VALUES (1,1,:ref)'), {'ref':reference})
        migration = load_migration('049_billing_numbering.py')
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            session = Session(connection, join_transaction_mode='create_savepoint')
            assert generate_quote_reference(session,1) == f'DEV-{year}-0013'
            assert generate_quote_reference(session,2) == f'DEV-{year}-0001'
            session.commit(); session.close()
            assert connection.execute(text('SELECT reference FROM quotes WHERE id=1')).scalar() == reference
            with pytest.raises(RuntimeError, match='counters'):
                migration.downgrade()
        connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_tag_dictionary_and_new_associations_are_separate(engine):
    with engine.connect() as connection, connection.begin():
        schema = 'migration_' + uuid4().hex
        connection.execute(text(f'CREATE SCHEMA {schema}'))
        connection.execute(text(f'SET LOCAL search_path TO {schema}'))
        for table in ['opportunities','tags']:
            connection.execute(text(f'CREATE TABLE {table} (id integer primary key)'))
        connection.execute(text('CREATE TABLE opportunity_tags (id integer primary key, name text)'))
        connection.execute(text("INSERT INTO opportunity_tags VALUES (1,'Preserved legacy tag')"))
        migration = load_migration('048_separate_tag_associations.py')
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text('SELECT name FROM opportunity_tags')).scalar() == 'Preserved legacy tag'
            migration.downgrade()
        connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
