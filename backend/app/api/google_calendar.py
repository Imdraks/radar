"""
Google Calendar Integration API
OAuth flow and calendar sync for deadlines
"""
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx

from app.db import get_db
from app.db.models.user import User
from app.db.models.opportunity import Opportunity, OpportunityStatus
from app.api.deps import get_current_user, get_current_workspace
from app.core import integration_oauth
from app.core.config import settings

router = APIRouter(prefix="/calendar/google", tags=["google-calendar"])

callback_router = APIRouter(prefix="/calendar/google", tags=["google-calendar"])

# Google Calendar API constants
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


class CalendarConnectionStatus(BaseModel):
    connected: bool
    email: Optional[str] = None
    calendar_id: Optional[str] = None
    last_sync: Optional[str] = None


class CalendarEvent(BaseModel):
    id: Optional[str] = None
    summary: str
    description: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    all_day: bool = True
    reminder_minutes: int = 60


class SyncResult(BaseModel):
    success: bool
    events_created: int
    events_updated: int
    errors: List[str]


# ============================================================================
# OAUTH FLOW
# ============================================================================

@router.get("/init")
async def init_google_calendar_oauth(
    request: Request,
    db: Session = Depends(get_db),
    workspace=Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
):
    """
    Initialize Google Calendar OAuth flow.
    Returns the authorization URL to redirect the user to.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    
    state = integration_oauth.issue(db, current_user, workspace, request, 'calendar')

    # Use different redirect URI for calendar (vs login)
    redirect_uri = f"{settings.backend_url}/api/v1/calendar/google/callback"
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_CALENDAR_SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return {"auth_url": auth_url, "state": state}


@callback_router.get("/callback")
async def google_calendar_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    Handle Google Calendar OAuth callback.
    Exchanges code for tokens and stores them for the user.
    """
    stored_state = integration_oauth.consume(db, state, 'calendar')
    user_id = stored_state['user_id']
    redirect_uri = f"{settings.backend_url}/api/v1/calendar/google/callback"
    
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
            )
            
            if response.status_code != 200:
                raise ValueError(f"Token exchange failed: {response.text}")
            
            tokens = response.json()
        
        # Get user email from Google
        async with httpx.AsyncClient() as client:
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            user_info = user_info_response.json()
        
        # Revalidate the originating account, session and workspace after Google
        # responds, and report success only if the server-side cache write works.
        integration_oauth.save_tokens(
            db, stored_state, f"google_calendar_tokens:{user_id}",
            {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": datetime.utcnow().timestamp() + tokens.get("expires_in", 3600),
                "email": user_info.get("email"),
            },
        )

        # Redirect to frontend settings page with success
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?tab=calendar&connected=true"
        )
        
    except Exception as e:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?tab=calendar&error=google_connection_failed"
        )


@router.get("/status", response_model=CalendarConnectionStatus)
async def get_calendar_status(
    current_user: User = Depends(get_current_user),
):
    """Check if user has connected Google Calendar"""
    from app.core.cache import cache_get
    
    tokens = cache_get(f"google_calendar_tokens:{current_user.id}")
    
    if not tokens:
        return CalendarConnectionStatus(connected=False)
    
    # Check if token is expired
    if tokens.get("expires_at", 0) < datetime.utcnow().timestamp():
        # Token expired, try to refresh
        if tokens.get("refresh_token"):
            try:
                new_tokens = await refresh_google_token(tokens["refresh_token"])
                from app.core.cache import cache_set
                cache_set(
                    f"google_calendar_tokens:{current_user.id}",
                    {**tokens, **new_tokens},
                    ttl=86400 * 30
                )
                tokens = {**tokens, **new_tokens}
            except Exception:
                return CalendarConnectionStatus(connected=False)
        else:
            return CalendarConnectionStatus(connected=False)
    
    return CalendarConnectionStatus(
        connected=True,
        email=tokens.get("email"),
        calendar_id="primary",
        last_sync=None  # TODO: Track last sync time
    )


@router.delete("/disconnect")
async def disconnect_calendar(
    current_user: User = Depends(get_current_user),
):
    """Disconnect Google Calendar integration"""
    from app.core.cache import cache_delete
    cache_delete(f"google_calendar_tokens:{current_user.id}")
    return {"success": True, "message": "Google Calendar disconnected"}


# ============================================================================
# CALENDAR EVENTS - List and manage events
# ============================================================================

class CalendarEventItem(BaseModel):
    id: str
    summary: str
    description: Optional[str] = None
    start: str
    end: str
    all_day: bool = False
    html_link: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None


@router.get("/events", response_model=List[CalendarEventItem])
async def list_calendar_events(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
):
    """
    List Google Calendar events within a date range.
    If no dates provided, returns events for the current month + next month.
    """
    from app.core.cache import cache_get
    
    tokens = cache_get(f"google_calendar_tokens:{current_user.id}")
    
    # Also check unified google tokens
    if not tokens:
        tokens = cache_get(f"google_tokens:{current_user.id}")
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Calendar non connecté. Veuillez connecter votre compte Google."
        )
    
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google invalide"
        )
    
    # Check if token is expired and refresh if needed
    if tokens.get("expires_at", 0) < datetime.utcnow().timestamp():
        if tokens.get("refresh_token"):
            try:
                new_tokens = await refresh_google_token(tokens["refresh_token"])
                from app.core.cache import cache_set
                cache_set(
                    f"google_calendar_tokens:{current_user.id}",
                    {**tokens, **new_tokens},
                    ttl=86400 * 30
                )
                access_token = new_tokens.get("access_token")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token Google expiré, veuillez vous reconnecter"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token Google expiré"
            )
    
    # Default date range: current month + next month
    if start_date:
        time_min = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        time_min = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if end_date:
        time_max = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    else:
        # 2 months from start
        if time_min.month >= 11:
            time_max = time_min.replace(year=time_min.year + 1, month=(time_min.month + 2) % 12 or 12)
        else:
            time_max = time_min.replace(month=time_min.month + 2)
    
    params = {
        "timeMin": time_min.isoformat() + "Z",
        "timeMax": time_max.isoformat() + "Z",
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 250,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Google Calendar: {response.text}"
            )
        
        data = response.json()
        events = []
        
        for item in data.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            
            events.append(CalendarEventItem(
                id=item["id"],
                summary=item.get("summary", "Sans titre"),
                description=item.get("description"),
                start=start.get("dateTime") or start.get("date", ""),
                end=end.get("dateTime") or end.get("date", ""),
                all_day="date" in start,
                html_link=item.get("htmlLink"),
                status=item.get("status"),
                location=item.get("location"),
            ))
        
        return events


@router.get("/calendars")
async def list_user_calendars(
    current_user: User = Depends(get_current_user),
):
    """List all calendars accessible by the user"""
    from app.core.cache import cache_get
    
    tokens = cache_get(f"google_calendar_tokens:{current_user.id}")
    if not tokens:
        tokens = cache_get(f"google_tokens:{current_user.id}")
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Calendar non connecté"
        )
    
    access_token = tokens.get("access_token")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"maxResults": 100},
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Erreur lors de la récupération des calendriers"
            )
        
        data = response.json()
        return [
            {
                "id": cal["id"],
                "summary": cal.get("summary", ""),
                "primary": cal.get("primary", False),
                "background_color": cal.get("backgroundColor"),
            }
            for cal in data.get("items", [])
        ]


# ============================================================================
# CALENDAR SYNC
# ============================================================================

@router.post("/sync")
async def sync_deadlines_to_calendar(
    opportunity_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncResult:
    """
    Sync opportunity deadlines to Google Calendar.
    If no IDs provided, syncs all active opportunities with deadlines.
    """
    from app.core.cache import cache_get
    
    tokens = cache_get(f"google_calendar_tokens:{current_user.id}")
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Calendar not connected"
        )
    
    # Get opportunities to sync
    query = db.query(Opportunity).filter(
        Opportunity.deadline_at.isnot(None),
        Opportunity.status.notin_([
            OpportunityStatus.WON,
            OpportunityStatus.LOST,
            OpportunityStatus.CANCELLED
        ])
    )
    
    if opportunity_ids:
        query = query.filter(Opportunity.id.in_(opportunity_ids))
    
    opportunities = query.limit(50).all()
    
    created = 0
    updated = 0
    errors = []
    
    access_token = tokens.get("access_token")
    
    async with httpx.AsyncClient() as client:
        for opp in opportunities:
            try:
                event_data = {
                    "summary": f"[Deadline] {opp.title[:50] if opp.title else 'Opportunité'}",
                    "description": f"Organisation: {opp.organization or 'N/A'}\nBudget: {opp.budget_amount or 'N/A'}€\nScore: {opp.score or 'N/A'}\n\nVoir: {settings.frontend_url}/leads/{opp.id}",
                    "start": {
                        "date": opp.deadline_at.strftime("%Y-%m-%d"),
                    },
                    "end": {
                        "date": (opp.deadline_at + timedelta(days=1)).strftime("%Y-%m-%d"),
                    },
                    "reminders": {
                        "useDefault": False,
                        "overrides": [
                            {"method": "popup", "minutes": 1440},  # 1 day before
                            {"method": "popup", "minutes": 10080},  # 1 week before
                        ]
                    },
                    "transparency": "transparent",
                }
                
                # Check if event already exists (by searching)
                # For simplicity, we create new events each time
                # In production, store event IDs and update instead
                
                response = await client.post(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=event_data,
                )
                
                if response.status_code in [200, 201]:
                    created += 1
                else:
                    errors.append(f"Failed to create event for {opp.id}: {response.text}")
                    
            except Exception as e:
                errors.append(f"Error syncing {opp.id}: {str(e)}")
    
    return SyncResult(
        success=len(errors) == 0,
        events_created=created,
        events_updated=updated,
        errors=errors[:5]  # Limit error messages
    )


@router.post("/sync-single/{opportunity_id}")
async def sync_single_deadline(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync a single opportunity deadline to Google Calendar"""
    result = await sync_deadlines_to_calendar(
        opportunity_ids=[opportunity_id],
        db=db,
        current_user=current_user,
    )
    return result


# ============================================================================
# HELPERS
# ============================================================================

async def refresh_google_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh an expired Google access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )
        
        if response.status_code != 200:
            raise ValueError("Failed to refresh token")
        
        tokens = response.json()
        return {
            "access_token": tokens.get("access_token"),
            "expires_at": datetime.utcnow().timestamp() + tokens.get("expires_in", 3600),
        }
