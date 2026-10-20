"""Tests require an explicitly disposable PostgreSQL URL; never use application DB defaults."""
import os
os.environ["TESTING"] = "true"
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.db.base import Base
from app.db import models
from app.db.models.artist_event import ArtistEvent
from app.db.models.user import User, Role
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.db.session import get_db
from app.core.security import create_access_token
from app.main import app


@pytest.fixture(scope="session")
def engine():
    url = os.environ.get("RADAR_TEST_DATABASE_URL")
    if not url:
        pytest.fail("RADAR_TEST_DATABASE_URL must identify a disposable PostgreSQL database")
    from uuid import uuid4
    from sqlalchemy import text
    schema = "radar_test_" + uuid4().hex
    admin_engine = create_engine(url)
    with admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def connection(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture
def db_session(connection):
    with Session(connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
        yield session


@pytest.fixture
def actors(db_session):
    users = [User(email=f"user{i}@radar.invalid", full_name=f"User {i}", role=Role.ADMIN if i in (0,2) else Role.PM,
                  is_active=True, is_whitelisted=True, is_superuser=(i == 2)) for i in range(4)]
    db_session.add_all(users)
    db_session.flush()
    workspaces = [Workspace(name=f"Agency {i}", owner_user_id=users[i].id, plan="core", enabled_packs=["core"], addons=[], max_seats=3) for i in range(2)]
    db_session.add_all(workspaces)
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspaces[0].id, user_id=users[3].id, role=WorkspaceRole.VIEWER))
    db_session.commit()
    return users, workspaces


@pytest.fixture
def headers(actors):
    return lambda index=0: {"Authorization": f"Bearer {create_access_token({'sub': str(actors[0][index].id)})}"}


@pytest.fixture
def client(connection, monkeypatch):
    def database():
        with Session(connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
            yield session
    app.dependency_overrides[get_db] = database
    monkeypatch.setattr("app.api.map_calendar.cache_get", lambda *args: None)
    monkeypatch.setattr("app.core.cache.cache_get", lambda *args: None)
    monkeypatch.setattr("app.workers.discovery_pipeline.run_enrichment_pipeline.delay", lambda *args: None)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
