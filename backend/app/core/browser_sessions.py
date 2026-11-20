"""Host-only HttpOnly sessions for browsers; API bearer clients remain supported."""

import time
from urllib.parse import urlsplit
from fastapi import HTTPException
from app.core.config import settings
from app.core.security import decode_token

MARKER = "cookie-session"


def is_marker(token):
    return isinstance(token, str) and (
        token == MARKER or token.startswith(MARKER + ".")
    )


def names():
    prefix = "__Host-" if settings.app_env == "production" else ""
    return prefix + "radar_access", prefix + "radar_refresh"


def require_origin(request):
    origin = request.headers.get("origin", "")
    expected = urlsplit(settings.frontend_url)
    allowed = f"{expected.scheme}://{expected.netloc}"
    if not origin or origin != allowed:
        raise HTTPException(403, "Origine de la requête non autorisée.")


def request_token(request, provided=None):
    token = (
        provided
        if provided is not None
        else request.headers.get("authorization", "").removeprefix("Bearer ")
    )
    if token and not is_marker(token):
        return token
    cookie = request.cookies.get(names()[0], "")
    if cookie and getattr(request, "method", "GET") not in {"GET", "HEAD", "OPTIONS"}:
        require_origin(request)
    if cookie and token and token.startswith(MARKER + "."):
        if (decode_token(cookie) or {}).get("sid") != token[len(MARKER) + 1 :]:
            return ""
    return cookie


def set_cookies(response, access, refresh):
    for name, token in zip(names(), (access, refresh)):
        payload = decode_token(token)
        if not payload:
            raise HTTPException(401, "Session invalide.")
        response.set_cookie(
            name,
            token,
            max_age=max(0, int(payload["exp"] - time.time())),
            secure=settings.app_env == "production",
            httponly=True,
            samesite="lax",
            path="/",
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def clear_cookies(response):
    for name in names():
        response.delete_cookie(
            name,
            path="/",
            secure=settings.app_env == "production",
            httponly=True,
            samesite="lax",
        )
