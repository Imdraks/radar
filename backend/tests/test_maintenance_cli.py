"""Operator inventory stays scoped and PostgreSQL-enforced read-only."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'tools/maintenance/list_clients.py'


def invoke(*args, url=None):
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'backend'), 'TESTING': 'true'}
    if url:
        env['DATABASE_URL'] = url
    return subprocess.run([sys.executable, str(TOOL), *args], env=env, capture_output=True, text=True, timeout=30)


@pytest.fixture
def inventory_database(engine):
    schema = 'radar_cli_' + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
        conn.execute(text(f'CREATE TABLE {schema}.workspaces (id integer PRIMARY KEY)'))
        for table in ['clients', 'billing_clients']:
            conn.execute(text(f'CREATE TABLE {schema}.{table} (id integer PRIMARY KEY, workspace_id integer NOT NULL, name text NOT NULL)'))
        conn.execute(text(f'INSERT INTO {schema}.workspaces VALUES (1),(2)'))
        conn.execute(text(f"INSERT INTO {schema}.clients VALUES (1,1,'TEST A'),(2,1,'TEST B'),(3,2,'OTHER ORGANIZATION')"))
        conn.execute(text(f"INSERT INTO {schema}.billing_clients VALUES (10,1,'TEST Billing'),(20,2,'OTHER BILLING')"))
    url = make_url(os.environ['RADAR_TEST_DATABASE_URL'])
    url = url.set(query={**url.query, 'options': '-csearch_path=' + schema})
    isolated = create_engine(url)
    try:
        yield isolated, url.render_as_string(hide_password=False)
    finally:
        isolated.dispose()
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_help_and_invalid_arguments_do_not_need_application_imports():
    assert invoke('--help').returncode == 0
    for args in [[], ['--workspace-id', '0'], ['--workspace-id', '-1'], ['--workspace-id', '1', '--limit', '501']]:
        result = invoke(*args)
        assert result.returncode == 2
        assert 'Traceback' not in result.stderr


def test_inventory_never_lists_a_different_workspace(inventory_database):
    _, url = inventory_database
    result = invoke('--workspace-id', '1', '--limit', '1', url=url)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload['crm'] == {'total': 2, 'items': [{'id': 1, 'name': 'TEST A'}]}
    assert payload['billing'] == {'total': 1, 'items': [{'id': 10, 'name': 'TEST Billing'}]}
    assert 'OTHER' not in result.stdout
    missing = invoke('--workspace-id', '999', url=url)
    assert missing.returncode != 0 and 'Workspace introuvable' in missing.stderr


def test_postgresql_blocks_an_accidental_write(inventory_database, monkeypatch):
    engine, _ = inventory_database
    spec = importlib.util.spec_from_file_location('maintenance_clients', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def session_factory():
        session = Session(engine)
        original_query = session.query
        def query(*args, **kwargs):
            # Simulate a future accidental mutation before the first query.
            session.execute(text('INSERT INTO workspaces(id) VALUES (999)'))
            return original_query(*args, **kwargs)
        session.query = query
        return session
    monkeypatch.setattr('app.db.session.SessionLocal', session_factory)
    with pytest.raises(DBAPIError) as error:
        module.main(['--workspace-id', '1'])
    assert error.value.orig.pgcode == '25006'
    with engine.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM workspaces WHERE id=999')).scalar_one() == 0
