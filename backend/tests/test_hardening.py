"""Credential encryption, upload boundaries, configuration and cache isolation."""

import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException, UploadFile
from cryptography.fernet import Fernet
from app.core.config import settings, Settings
from app.core.encryption import encrypt_sensitive, decrypt_sensitive
from app.core.credential_cache import encode, decode


def test_credential_envelopes_are_authenticated_and_bound_to_owner():
    key = "google_workspace_tokens:1"
    raw = encode(
        key, {"access_token": "PRIVATE-ACCESS", "refresh_token": "PRIVATE-REFRESH"}
    )
    assert "PRIVATE-" not in raw
    assert decode(key, raw)["access_token"] == "PRIVATE-ACCESS"
    with pytest.raises(ValueError):
        decode("google_workspace_tokens:2", raw)
    with pytest.raises(Exception):
        decode(key, raw[:-10] + "corrupt")
    assert decode(key, '{"access_token":"legacy"}')["access_token"] == "legacy"


def test_new_encryption_key_keeps_legacy_data_readable_and_allows_rotation(monkeypatch):
    monkeypatch.setattr(settings, "data_encryption_key", "")
    old = encrypt_sensitive("Existing private data")
    first = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "data_encryption_key", first)
    assert decrypt_sensitive(old) == "Existing private data"
    new = encrypt_sensitive("New private data")
    second = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "data_encryption_key", second)
    monkeypatch.setattr(settings, "data_encryption_previous_keys", first)
    assert decrypt_sensitive(new) == "New private data"
    assert decrypt_sensitive(old) == "Existing private data"
    assert decrypt_sensitive("invalid-ciphertext") == ""


def test_production_configuration_rejects_debug_http_and_short_keys():
    s = Settings(
        _env_file=None,
        app_env="production",
        debug=True,
        secret_key="short",
        jwt_secret_key="short",
        frontend_url="http://radarapp.fr",
        data_encryption_key="invalid",
    )
    warnings = s.validate_security_settings()
    assert any("debug=True" in w and "CRITICAL" in w for w in warnings)
    assert any("HTTPS" in w for w in warnings)
    assert any("32 characters" in w for w in warnings)
    assert any("invalid data encryption" in w for w in warnings)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.googleapis.com/upload",
        "https://www.googleapis.com.evil.example/upload",
        "https://127.0.0.1/internal",
        "https://user:password@www.googleapis.com/upload",
        "https://www.googleapis.com:444/upload",
    ],
)
def test_upload_never_forwards_data_to_arbitrary_hosts(url):
    from app.services.safe_provider_url import google_upload_url

    with pytest.raises(ValueError):
        google_upload_url(url)


def test_upload_validation_is_preserved_and_temporary_file_closed(monkeypatch):
    from app.api.google_drive import upload_file_to_drive

    service = SimpleNamespace(get_access_token=AsyncMock(return_value="PRIVATE-TOKEN"))
    monkeypatch.setattr(
        "app.api.google_drive.get_google_workspace_service", lambda id: service
    )
    monkeypatch.setattr(
        "app.core.advanced_security.validate_file_upload",
        lambda *args, **kwargs: (False, "Fichier refusé"),
    )
    f = UploadFile(BytesIO(b"forbidden"), filename="test.pdf")
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            upload_file_to_drive(
                file=f,
                folder_id="root",
                file_name=None,
                current_user=SimpleNamespace(id=1),
            )
        )
    assert error.value.status_code == 400
    assert f.file.closed


def test_oauth_account_fields_migrate_without_logging_values(db_session, actors):
    from app.db.models.account import Account
    from app.core.credential_cache import migrate_accounts

    a = Account(
        user_id=actors[0][0].id,
        provider="google",
        provider_account_id="TEST",
        access_token="PRIVATE-ACCESS",
        refresh_token="PRIVATE-REFRESH",
    )
    db_session.add(a)
    db_session.commit()
    assert migrate_accounts(db_session) >= 2
    assert a.access_token.startswith("enc:") and "PRIVATE-ACCESS" not in a.access_token
    assert decrypt_sensitive(a.access_token[4:]) == "PRIVATE-ACCESS"


def test_total_request_limit_catches_headers_and_chunked_bodies_before_consumption():
    from app.core.request_limits import RequestSizeLimitMiddleware

    hits = []

    async def app(scope, receive, send):
        while (await receive()).get("more_body"):
            pass
        hits.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def run(headers):
        responses = []
        chunks = iter(
            [
                {"type": "http.request", "body": b"1234", "more_body": True},
                {"type": "http.request", "body": b"56789", "more_body": False},
            ]
        )

        async def receive():
            return next(chunks)

        async def send(message):
            responses.append(message)

        await RequestSizeLimitMiddleware(app, max_bytes=8)(
            {"type": "http", "headers": headers}, receive, send
        )
        return responses[0]["status"]

    assert asyncio.run(run([(b"content-length", b"999")])) == 413
    assert asyncio.run(run([])) == 413
    assert hits == []


def test_binary_encryption_preserves_bytes_and_prevents_cross_field_substitution(
    db_session, actors
):
    from app.core.encrypted_binary import (
        encrypt_binary,
        decrypt_binary,
        migrate_binaries,
        PREFIX,
    )
    from sqlalchemy import text

    raw = b"PRIVATE-LOCAL-BINARY"
    encrypted = encrypt_binary(raw, "user-avatar")
    assert raw not in encrypted
    assert decrypt_binary(encrypted, "user-avatar") == raw
    with pytest.raises(ValueError):
        decrypt_binary(encrypted, "platform-contract")
    with pytest.raises(ValueError):
        decrypt_binary(encrypted[:-1] + bytes([encrypted[-1] ^ 1]), "user-avatar")
    db_session.execute(
        text("UPDATE users SET avatar_image=:value WHERE id=:id"),
        {"value": raw, "id": actors[0][0].id},
    )
    db_session.commit()
    assert migrate_binaries(db_session) >= 1
    persisted = bytes(
        db_session.execute(
            text("SELECT avatar_image FROM users WHERE id=:id"), {"id": actors[0][0].id}
        ).scalar_one()
    )
    assert persisted.startswith(PREFIX) and raw not in persisted
    db_session.refresh(actors[0][0])
    assert actors[0][0].avatar_image == raw


def test_sensitive_field_migration_preserves_totp_and_moves_to_primary_key(
    db_session, actors, monkeypatch
):
    from app.core.credential_cache import migrate_fernet_fields
    from cryptography.fernet import Fernet

    monkeypatch.setattr(settings, "data_encryption_key", "")
    user = actors[0][0]
    old = encrypt_sensitive("verified@example.com")
    user.mfa_email = old
    user.two_factor_secret = "JBSWY3DPEHPK3PXP"
    db_session.commit()
    primary = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "data_encryption_key", primary)
    assert migrate_fernet_fields(db_session) >= 2
    db_session.refresh(user)
    assert user.mfa_email != old
    assert (
        Fernet(primary.encode()).decrypt(user.mfa_email.encode()).decode()
        == "verified@example.com"
    )
    assert (
        Fernet(primary.encode()).decrypt(user.two_factor_secret[4:].encode()).decode()
        == "JBSWY3DPEHPK3PXP"
    )


def test_prepare_security_config_never_rotates_existing_secrets(tmp_path, capsys):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "prepare_security_config",
        Path(__file__).parents[2] / "scripts/prepare_security_config.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / ".env"
    path.write_text("SECRET_KEY=PRIVATE-LEGACY-KEY\nJWT_SECRET_KEY=PRIVATE-JWT-KEY\n")
    module.prepare(tmp_path)
    first = path.read_text()
    module.prepare(tmp_path)
    assert path.read_text() == first
    assert (
        "SECRET_KEY=PRIVATE-LEGACY-KEY" in first
        and "JWT_SECRET_KEY=PRIVATE-JWT-KEY" in first
    )
    assert "DATA_ENCRYPTION_KEY=" in first
    assert path.stat().st_mode & 0o077 == 0
    assert "PRIVATE" not in capsys.readouterr().out


def test_bound_session_migration_refuses_security_downgrade(engine):
    from test_migrations import load_migration
    from uuid import uuid4
    from sqlalchemy import text
    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    schema = "bound_" + uuid4().hex
    with engine.connect() as connection, connection.begin():
        connection.execute(text(f"CREATE SCHEMA {schema}"))
        connection.execute(text(f"SET LOCAL search_path TO {schema}"))
        connection.execute(
            text(
                "CREATE TABLE user_sessions(id integer primary key, revoked_at timestamp)"
            )
        )
        m = load_migration("067_browser_key_binding.py")
        with Operations.context(MigrationContext.configure(connection)):
            m.upgrade()
            m.downgrade()
            m.upgrade()
            connection.execute(
                text("INSERT INTO user_sessions(id,browser_public_key) VALUES(1,'{}')")
            )
            with pytest.raises(RuntimeError):
                m.downgrade()
            connection.execute(text("UPDATE user_sessions SET revoked_at=now()"))
            m.downgrade()
        connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
