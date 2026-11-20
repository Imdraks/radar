"""Browser cookies alone, or copied signed requests, must never authenticate elsewhere."""

import base64, time, secrets
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives import hashes
from app.core.config import settings
from app.core.security import decode_token
from app.core.mfa import issue_tokens


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


class Device:
    def __init__(self, sid):
        self.sid = sid
        self.key = ec.generate_private_key(ec.SECP256R1())
        n = self.key.public_key().public_numbers()
        self.jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": b64(n.x.to_bytes(32, "big")),
            "y": b64(n.y.to_bytes(32, "big")),
        }

    def headers(self, method, path, issued=None):
        issued = str(int(time.time()) if issued is None else issued)
        nonce = secrets.token_hex(16)
        message = "\n".join([self.sid, method, path, issued, nonce]).encode()
        r, s = decode_dss_signature(self.key.sign(message, ec.ECDSA(hashes.SHA256())))
        return {
            "Origin": settings.frontend_url,
            "X-Radar-Session": self.sid,
            "X-Radar-Issued": issued,
            "X-Radar-Nonce": nonce,
            "X-Radar-Proof": b64(r.to_bytes(32, "big") + s.to_bytes(32, "big")),
        }


@pytest.fixture(autouse=True)
def nonce_store(monkeypatch):
    class Store:
        def __init__(self):
            self.values = {}

        def set(self, key, value, nx=False, ex=None):
            if nx and key in self.values:
                return False
            self.values[key] = value
            return True

        def setex(self, key, ttl, value):
            self.values[key] = value
            return True

        def getdel(self, key):
            return self.values.pop(key, None)

    store = Store()
    monkeypatch.setattr("app.core.cache.redis_client", store)
    return store


def session(db, user):
    tokens = issue_tokens(user)
    db.commit()
    return tokens, Device(decode_token(tokens["access_token"])["sid"])


def enroll(client, t, d):
    p = "/api/v1/auth/browser/session"
    r = client.post(
        p,
        headers={
            **d.headers("POST", p),
            "Authorization": "Bearer " + t["access_token"],
        },
        json={"refresh_token": t["refresh_token"], "public_key": d.jwk},
    )
    assert r.status_code == 200, r.text
    return r


def test_bound_cookie_requires_private_key_and_replay_is_refused(
    client, actors, db_session
):
    t, d = session(db_session, actors[0][0])
    r = enroll(client, t, d)
    assert all(
        "HttpOnly" in c and "SameSite=lax" in c
        for c in r.headers.get_list("set-cookie")
    )
    p = "/api/v1/auth/sessions"
    assert client.get(p).status_code == 401  # All cookies copied, no device key.
    h = d.headers("GET", p)
    assert client.get(p, headers=h).status_code == 200
    assert (
        client.get(p, headers=h).status_code == 401
    )  # Exact request copied from browser history.
    attacker = Device(d.sid)
    assert client.get(p, headers=attacker.headers("GET", p)).status_code == 401
    assert (
        client.get(p, headers=d.headers("GET", p, int(time.time()) - 120)).status_code
        == 401
    )
    assert (
        client.get(
            p, headers={**d.headers("GET", p), "X-Forwarded-For": "203.0.113.55"}
        ).status_code
        == 200
    )
    # A captured JWT from a browser-bound session must not bypass the proof either.
    assert (
        client.get(
            p, headers={"Authorization": "Bearer " + t["access_token"]}
        ).status_code
        == 401
    )


def test_origin_refresh_and_logout_bound_to_same_session(client, actors, db_session):
    t, d = session(db_session, actors[0][0])
    enroll(client, t, d)
    p = "/api/v1/auth/sessions/revoke-others"
    assert (
        client.post(
            p, headers={**d.headers("POST", p), "Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.post(p, headers=d.headers("POST", p)).status_code == 200
    p = "/api/v1/auth/refresh"
    assert (
        client.post(
            p,
            headers={"Origin": settings.frontend_url},
            json={"refresh_token": "cookie-session"},
        ).status_code
        == 401
    )
    r = client.post(
        p, headers=d.headers("POST", p), json={"refresh_token": "cookie-session"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["access_token"] == "cookie-session." + d.sid
    p = "/api/v1/auth/logout"
    r = client.post(p, headers=d.headers("POST", p))
    assert r.status_code == 200, r.text
    assert "Max-Age=0" in r.headers["set-cookie"]
    assert (
        client.get(
            "/api/v1/auth/sessions",
            headers={"Authorization": "Bearer " + t["access_token"]},
        ).status_code
        == 401
    )


def test_exchange_rejects_foreign_origin_and_mismatched_refresh(
    client, actors, db_session
):
    t, d = session(db_session, actors[0][0])
    other, _ = session(db_session, actors[0][1])
    p = "/api/v1/auth/browser/session"
    h = {**d.headers("POST", p), "Authorization": "Bearer " + t["access_token"]}
    r = client.post(
        p,
        headers={**h, "Origin": "https://evil.example"},
        json={"refresh_token": t["refresh_token"], "public_key": d.jwk},
    )
    assert r.status_code == 403
    r = client.post(
        p,
        headers=h,
        json={"refresh_token": other["refresh_token"], "public_key": d.jwk},
    )
    assert r.status_code == 401


def test_production_cookies_secure_host_only(client, actors, db_session, monkeypatch):
    t, d = session(db_session, actors[0][0])
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "frontend_url", "https://radarapp.fr")
    r = enroll(client, t, d)
    for value in r.headers.get_list("set-cookie"):
        assert "__Host-radar_" in value and "Secure" in value and "HttpOnly" in value
        assert "Domain=" not in value and "Path=/" in value


def test_unbound_native_bearer_stays_compatible_and_marker_alone_fails(client, headers):
    assert (
        client.get(
            "/api/v1/auth/sessions", headers={"Authorization": "Bearer cookie-session"}
        ).status_code
        == 401
    )
    assert client.get("/api/v1/auth/sessions", headers=headers()).status_code == 200


def test_browser_key_cannot_be_replaced_with_copied_cookie(client, actors, db_session):
    t, d = session(db_session, actors[0][0])
    enroll(client, t, d)
    p = "/api/v1/auth/browser/session"
    attacker = Device(d.sid)
    r = client.post(
        p,
        headers=attacker.headers("POST", p),
        json={"refresh_token": t["refresh_token"], "public_key": attacker.jwk},
    )
    assert r.status_code == 401
    r = client.post(
        p,
        headers=d.headers("POST", p),
        json={"refresh_token": t["refresh_token"], "public_key": attacker.jwk},
    )
    assert r.status_code == 409


def test_websocket_ticket_is_one_use_and_workspace_bound(client, actors, db_session):
    from app.core.device_proof import consume_ticket

    t, d = session(db_session, actors[0][0])
    enroll(client, t, d)
    p = "/api/v1/auth/browser/websocket-ticket"
    r = client.post(p, headers=d.headers("POST", p))
    assert r.status_code == 200, r.text
    grant = consume_ticket(r.json()["ticket"])
    assert grant["sid"] == d.sid and grant["workspace_id"] == actors[1][0].id
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        consume_ticket(r.json()["ticket"])


def test_nonce_service_failure_is_closed(
    client, actors, db_session, nonce_store, monkeypatch
):
    t, d = session(db_session, actors[0][0])
    enroll(client, t, d)
    monkeypatch.setattr(
        nonce_store,
        "set",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("PRIVATE REDIS ERROR")),
    )
    p = "/api/v1/auth/sessions"
    r = client.get(p, headers=d.headers("GET", p))
    assert r.status_code == 503
    assert "PRIVATE" not in r.text
