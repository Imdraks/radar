"""Sender-constrained browser sessions: P-256 proof and single-use request nonces."""

import base64
import hashlib
import json
import re
import time
import secrets
from fastapi import HTTPException
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature


def unpack(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def public_key(jwk):
    if (
        not isinstance(jwk, dict)
        or jwk.get("kty") != "EC"
        or jwk.get("crv") != "P-256"
        or "d" in jwk
    ):
        raise ValueError("Invalid public key")
    x, y = unpack(jwk["x"]), unpack(jwk["y"])
    if len(x) != 32 or len(y) != 32:
        raise ValueError("Invalid coordinates")
    return ec.EllipticCurvePublicNumbers(
        int.from_bytes(x, "big"), int.from_bytes(y, "big"), ec.SECP256R1()
    ).public_key()


def target(request):
    path = request.scope.get("raw_path", request.url.path.encode()).decode("ascii")
    query = request.scope.get("query_string", b"").decode("ascii")
    return path + ("?" + query if query else "")


def verify(request, session, jwk=None):
    if request.scope["type"] == "websocket":
        if getattr(request.state, "browser_device_verified", None) == str(session.id):
            return
        raise HTTPException(401, "Cette session exige la clé de son navigateur.")
    sid = request.headers.get("x-radar-session", "")
    issued = request.headers.get("x-radar-issued", "")
    nonce = request.headers.get("x-radar-nonce", "")
    signature = request.headers.get("x-radar-proof", "")
    try:
        if (
            sid != str(session.id)
            or not issued.isdecimal()
            or abs(time.time() - int(issued)) > 60
            or not re.fullmatch("[a-f0-9]{32}", nonce)
            or len(signature) > 128
        ):
            raise ValueError()
        raw = unpack(signature)
        if len(raw) != 64:
            raise ValueError()
        message = "\n".join(
            [sid, request.method.upper(), target(request), issued, nonce]
        ).encode()
        public_key(jwk or session.browser_public_key).verify(
            encode_dss_signature(
                int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
            ),
            message,
            ec.ECDSA(hashes.SHA256()),
        )
    except (ValueError, TypeError, KeyError, InvalidSignature, UnicodeError):
        raise HTTPException(
            401, "Preuve de navigateur invalide ou expirée. Reconnectez-vous."
        ) from None
    from app.core.cache import redis_client

    try:
        accepted = redis_client.set(
            "radar:browser-proof:" + sid + ":" + nonce, "1", nx=True, ex=180
        )
    except Exception:
        raise HTTPException(
            503, "La vérification de session est temporairement indisponible."
        ) from None
    if not accepted:
        raise HTTPException(401, "Cette preuve de session a déjà été utilisée.")


def ticket(session, workspace_id):
    from app.core.cache import redis_client

    value = secrets.token_urlsafe(32)
    try:
        if not redis_client.setex(
            "radar:ws-ticket:" + hashlib.sha256(value.encode()).hexdigest(),
            30,
            json.dumps({"sid": str(session.id), "workspace_id": workspace_id}),
        ):
            raise RuntimeError()
    except Exception:
        raise HTTPException(503, "Connexion temps réel indisponible.") from None
    return value


def consume_ticket(value):
    from app.core.cache import redis_client

    try:
        if len(value) > 100:
            raise ValueError()
        raw = redis_client.getdel(
            "radar:ws-ticket:" + hashlib.sha256(value.encode()).hexdigest()
        )
        if not raw:
            raise ValueError()
        return json.loads(raw)
    except Exception:
        raise HTTPException(401, "Connexion temps réel invalide ou expirée.") from None
