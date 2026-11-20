"""Exchange already-authenticated native credentials for protected browser cookies."""

from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel, Field
from app.api.deps import get_current_user, get_db
from app.core.browser_sessions import require_origin, set_cookies, request_token
from app.core.security import decode_token, verify_token
from app.core.login_sessions import require_session

router = APIRouter(prefix="/auth/browser")


class Exchange(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=8192)
    public_key: dict


@router.post("/session")
def exchange(
    data: Exchange,
    request: Request,
    response: Response,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_origin(request)
    access = request_token(request)
    a = decode_token(access) or {}
    r = decode_token(data.refresh_token) or {}
    if (
        verify_token(data.refresh_token, "refresh") != str(user.id)
        or r.get("sid") != a.get("sid")
        or r.get("mfa_ver", 0) != (user.mfa_version or 0)
    ):
        raise HTTPException(401, "Identifiants de session incompatibles.")
    session = require_session(db, user, r, lock=True)
    from app.core.device_proof import verify, public_key

    try:
        public_key(data.public_key)
    except (ValueError, TypeError, KeyError):
        raise HTTPException(422, "Clé publique invalide.") from None
    normalized = {key: data.public_key[key] for key in ("kty", "crv", "x", "y")}
    if session.browser_public_key:
        if normalized != session.browser_public_key:
            raise HTTPException(
                409,
                "La clé de ce navigateur ne peut pas être remplacée sans reconnexion.",
            )
    else:
        verify(request, session, normalized)
        session.browser_public_key = normalized
        db.commit()
    set_cookies(response, access, data.refresh_token)
    return {"authenticated": True, "session_id": str(session.id)}


@router.post("/websocket-ticket")
def websocket_ticket(
    request: Request, user=Depends(get_current_user), db=Depends(get_db)
):
    from app.api.deps import resolve_workspace_id
    from app.core.device_proof import ticket

    session = require_session(db, user, decode_token(request_token(request)) or {})
    selected = request.query_params.get("workspace_id")
    if selected and (not selected.isdecimal() or len(selected) > 10):
        raise HTTPException(422, "Espace invalide")
    workspace_id = resolve_workspace_id(db, user, int(selected) if selected else None)
    return {"ticket": ticket(session, workspace_id)}
