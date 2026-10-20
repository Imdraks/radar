"""Safety and real authentication for the disposable Codespaces bootstrap."""
import importlib.util
from pathlib import Path
import os
import stat
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("radar_codespaces", Path(__file__).resolve().parents[2] / ".devcontainer/radar.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def test_preview_config_requires_container_and_keeps_private_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(preview, "STATE", tmp_path / "state")
    monkeypatch.delenv("RADAR_CODESPACES_SANDBOX", raising=False)
    with pytest.raises(RuntimeError):
        preview.configuration()
    assert not preview.STATE.exists()
    monkeypatch.setenv("RADAR_CODESPACES_SANDBOX", "1")
    first = preview.configuration()
    assert first == preview.configuration()
    assert len(first["password"]) >= 30
    assert stat.S_IMODE((preview.STATE / "account.json").stat().st_mode) == 0o600


def test_preview_ignores_inherited_production_database_and_mail(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://production.example/live")
    monkeypatch.setenv("SMTP_PASSWORD", "test-inherited-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test-inherited-secret")
    monkeypatch.setenv("CODESPACE_NAME", "radar-test")
    env = preview.environment({"secret_key": "test-secret", "jwt_secret_key": "test-jwt", "password": "test-password"})
    assert env["DATABASE_URL"] == preview.DATABASE_URL
    assert env["FRONTEND_URL"] == "https://radar-test-3000.app.github.dev"
    assert "SMTP_PASSWORD" not in env and "OPENAI_API_KEY" not in env
    assert env["SEND_INVITATION_EMAILS"] == "false"
    assert env["NEXT_PUBLIC_API_URL"] == ""


@pytest.fixture
def empty_preview_engine():
    url = os.environ.get("RADAR_TEST_DATABASE_URL")
    if not url:
        pytest.fail("RADAR_TEST_DATABASE_URL must identify a disposable PostgreSQL database")
    schema = "radar_preview_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_preview_initialization_login_and_repeat_preserve_user_data(empty_preview_engine, tmp_path, monkeypatch):
    from app.main import app
    from app.db.session import get_db
    from app.db.models.user import User
    from app.db.models.workspace import Workspace
    monkeypatch.setenv("RADAR_CODESPACES_SANDBOX", "1")
    monkeypatch.setattr(preview, "STATE", tmp_path)
    data = preview.configuration()
    assert preview.initialize_database(empty_preview_engine, data) is True
    with Session(empty_preview_engine) as db:
        workspace = db.query(Workspace).one()
        workspace.name = "TEST — nom modifié par utilisateur"
        db.commit()
    assert preview.initialize_database(empty_preview_engine, data) is False
    with Session(empty_preview_engine) as db:
        assert db.query(User).count() == 1
        assert db.query(User).one().is_superuser is False
        assert db.query(Workspace).one().name == "TEST — nom modifié par utilisateur"
    def database():
        with Session(empty_preview_engine) as db:
            yield db
    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", json={"email": data["email"], "password": data["password"]})
            assert response.status_code == 200, response.text
            token = response.json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            response = client.get("/api/v1/subscription/current", headers=headers)
            assert response.status_code == 200, response.text
            assert response.json()["plan"] == "business"
            assert client.get("/health/detailed", headers=headers).status_code == 403
            assert client.post("/api/v1/auth/setup", json={"email": data["email"], "password": data["password"], "full_name": "test"}).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_preview_refuses_unrecognized_nonempty_database(empty_preview_engine):
    with empty_preview_engine.begin() as conn:
        conn.execute(text("CREATE TABLE existing_customer_data (value TEXT)"))
        conn.execute(text("INSERT INTO existing_customer_data VALUES ('preserve me')"))
    with pytest.raises(RuntimeError, match="non reconnue"):
        preview.initialize_database(empty_preview_engine, {"instance_id": "another-instance"})
    with empty_preview_engine.connect() as conn:
        assert conn.execute(text("SELECT value FROM existing_customer_data")).scalar_one() == "preserve me"


def test_preview_refuses_other_instance(empty_preview_engine):
    with empty_preview_engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE {preview.MARKER} (instance_id TEXT PRIMARY KEY)"))
        conn.execute(text(f"INSERT INTO {preview.MARKER} VALUES ('original-instance')"))
    with pytest.raises(RuntimeError, match="autre préversion"):
        preview.initialize_database(empty_preview_engine, {"instance_id": "new-instance"})
