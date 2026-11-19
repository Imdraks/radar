"""Real WebAuthn verification using signed ES256 assertions, not mocked verifiers."""

import base64
import hashlib
import json
import secrets
import cbor2
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from app.core.security import get_password_hash
from app.db.models.passkey import PasskeyCredential


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def raw(value):
    return base64.urlsafe_b64decode(value + "=" * ((-len(value)) % 4))


ORIGIN = "https://radarapp.fr"
RP = "radarapp.fr"
PASSWORD = "Initial-Secure!2026"


def registration(options, origin=ORIGIN, uv=True):
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_numbers()
    credential_id = secrets.token_bytes(32)
    cose = cbor2.dumps(
        {
            1: 2,
            3: -7,
            -1: 1,
            -2: public.x.to_bytes(32, "big"),
            -3: public.y.to_bytes(32, "big"),
        }
    )
    authdata = (
        hashlib.sha256(RP.encode()).digest()
        + bytes([0x45 if uv else 0x41])
        + bytes(4)
        + bytes(16)
        + len(credential_id).to_bytes(2, "big")
        + credential_id
        + cose
    )
    clientdata = json.dumps(
        {
            "type": "webauthn.create",
            "challenge": options["publicKey"]["challenge"],
            "origin": origin,
        }
    ).encode()
    credential = {
        "id": b64(credential_id),
        "rawId": b64(credential_id),
        "type": "public-key",
        "response": {
            "clientDataJSON": b64(clientdata),
            "attestationObject": b64(
                cbor2.dumps({"fmt": "none", "authData": authdata, "attStmt": {}})
            ),
        },
    }
    return credential, key, credential_id


def assertion(options, key, credential_id, origin=ORIGIN, counter=1, uv=True):
    authdata = (
        hashlib.sha256(RP.encode()).digest()
        + bytes([0x05 if uv else 0x01])
        + counter.to_bytes(4, "big")
    )
    clientdata = json.dumps(
        {
            "type": "webauthn.get",
            "challenge": options["publicKey"]["challenge"],
            "origin": origin,
        }
    ).encode()
    signature = key.sign(
        authdata + hashlib.sha256(clientdata).digest(), ec.ECDSA(hashes.SHA256())
    )
    return {
        "id": b64(credential_id),
        "rawId": b64(credential_id),
        "type": "public-key",
        "response": {
            "clientDataJSON": b64(clientdata),
            "authenticatorData": b64(authdata),
            "signature": b64(signature),
            "userHandle": None,
        },
    }


@pytest.fixture
def owner(client, headers, actors, db_session, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "frontend_url", ORIGIN)
    user = actors[0][0]
    user.email = "passkey-user@example.com"
    user.hashed_password = get_password_hash(PASSWORD)
    db_session.commit()
    return user, headers(0)


def start_registration(client, authorization):
    proof = client.post(
        "/api/v1/auth/mfa/reauth/start",
        headers=authorization,
        json={"password": PASSWORD},
    )
    assert proof.status_code == 200, proof.text
    options = client.post(
        "/api/v1/auth/passkeys/register/options",
        headers=authorization,
        json={"management_token": proof.json()["management_token"]},
    )
    assert options.status_code == 200, options.text
    return options.json()


def enroll(client, authorization):
    options = start_registration(client, authorization)
    credential, key, id = registration(options)
    response = client.post(
        "/api/v1/auth/passkeys/register/complete",
        headers=authorization,
        json={
            "challenge_id": options["challenge_id"],
            "name": "TEST key",
            "credential": credential,
        },
    )
    assert response.status_code == 200, response.text
    return response.json(), key, id


def login_options(client, email):
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    assert login.json()["requires_2fa"] and "passkey" in login.json()["methods"]
    token = login.json()["temp_token"]
    options = client.post(
        "/api/v1/auth/passkeys/authenticate/options", json={"challenge_token": token}
    )
    assert options.status_code == 200, options.text
    return token, options.json()


def test_passkey_registration_login_and_one_use_challenge(client, owner, db_session):
    user, authorization = owner
    enrolled, key, id = enroll(client, authorization)
    assert len(enrolled["backup_codes"]) == 10
    assert db_session.query(PasskeyCredential).filter_by(user_id=user.id).count() == 1
    token, options = login_options(client, user.email)
    payload = {
        "challenge_token": token,
        "challenge_id": options["challenge_id"],
        "credential": assertion(options, key, id),
    }
    response = client.post("/api/v1/auth/passkeys/authenticate/complete", json=payload)
    assert response.status_code == 200, response.text
    assert "access_token" in response.json()
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer " + response.json()["access_token"]},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/passkeys/authenticate/complete", json=payload
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    "origin,uv", [("https://evil.example.com", True), (ORIGIN, False)]
)
def test_registration_requires_correct_origin_and_user_verification(
    client, owner, db_session, origin, uv
):
    _, authorization = owner
    options = start_registration(client, authorization)
    credential, _, _ = registration(options, origin=origin, uv=uv)
    payload = {
        "challenge_id": options["challenge_id"],
        "name": "Rejected key",
        "credential": credential,
    }
    assert (
        client.post(
            "/api/v1/auth/passkeys/register/complete",
            headers=authorization,
            json=payload,
        ).status_code
        == 400
    )
    assert db_session.query(PasskeyCredential).count() == 0
    assert (
        client.post(
            "/api/v1/auth/passkeys/register/complete",
            headers=authorization,
            json=payload,
        ).status_code
        == 401
    )


def test_registration_cannot_use_another_accounts_ceremony(
    client, owner, headers, db_session
):
    _, authorization = owner
    options = start_registration(client, authorization)
    credential, _, _ = registration(options)
    assert (
        client.post(
            "/api/v1/auth/passkeys/register/complete",
            headers=headers(1),
            json={
                "challenge_id": options["challenge_id"],
                "name": "Wrong account",
                "credential": credential,
            },
        ).status_code
        == 401
    )
    assert db_session.query(PasskeyCredential).count() == 0


@pytest.mark.parametrize(
    "origin,uv", [("https://evil.example.com", True), (ORIGIN, False)]
)
def test_assertion_rejects_wrong_origin_and_missing_user_verification(
    client, owner, origin, uv
):
    user, authorization = owner
    _, key, id = enroll(client, authorization)
    token, options = login_options(client, user.email)
    result = client.post(
        "/api/v1/auth/passkeys/authenticate/complete",
        json={
            "challenge_token": token,
            "challenge_id": options["challenge_id"],
            "credential": assertion(options, key, id, origin=origin, uv=uv),
        },
    )
    assert result.status_code == 401, result.text
    assert "access_token" not in result.json()


def test_passkey_expiry_and_nonincreasing_counter_never_issue_tokens(
    client, owner, db_session
):
    from datetime import datetime, timedelta
    from uuid import UUID
    from app.db.models.passkey import PasskeyChallenge

    user, authorization = owner
    _, key, id = enroll(client, authorization)
    token, options = login_options(client, user.email)
    ceremony = db_session.get(PasskeyChallenge, UUID(options["challenge_id"]))
    ceremony.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    result = client.post(
        "/api/v1/auth/passkeys/authenticate/complete",
        json={
            "challenge_token": token,
            "challenge_id": options["challenge_id"],
            "credential": assertion(options, key, id),
        },
    )
    assert result.status_code == 401 and "access_token" not in result.json()
    stored = db_session.query(PasskeyCredential).filter_by(user_id=user.id).one()
    stored.sign_count = 10
    db_session.commit()
    token, options = login_options(client, user.email)
    result = client.post(
        "/api/v1/auth/passkeys/authenticate/complete",
        json={
            "challenge_token": token,
            "challenge_id": options["challenge_id"],
            "credential": assertion(options, key, id, counter=9),
        },
    )
    assert result.status_code == 401 and "access_token" not in result.json()
