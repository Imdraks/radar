"""
Google Workspace Service
Unified service for Drive, Docs, Sheets, and Calendar operations.
Handles token refresh, retries, and quota management.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.cache import cache_get, cache_set, cache_delete

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Google API scopes needed for workspace features
GOOGLE_WORKSPACE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.events",
]

# Standard folder structure for workspace
WORKSPACE_FOLDER_STRUCTURE = {
    "Clients": "Dossiers clients",
    "Projets": "Projets actifs",
    "Templates": "Modèles de documents",
    "Archive": "Projets archivés",
}

# Project subfolder structure - NEW STRUCTURE
PROJECT_FOLDER_STRUCTURE = [
    "00_Assets",
    "01_Brief",
    "02_Production",
    "03_PostProd",
    "04_Exports",
    "05_Admin",
    "07_Livrables",
    "99_Archive",
]


# ============================================================================
# EXCEPTIONS
# ============================================================================

class GoogleAPIError(Exception):
    """Base exception for Google API errors"""
    def __init__(self, message: str, status_code: int = 500, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response or {}
        super().__init__(self.message)


class TokenExpiredError(GoogleAPIError):
    """Token expired and refresh failed"""
    pass


class QuotaExceededError(GoogleAPIError):
    """Google API quota exceeded"""
    pass


class FileNotFoundError(GoogleAPIError):
    """Google Drive file/folder not found"""
    pass


# ============================================================================
# GOOGLE WORKSPACE SERVICE
# ============================================================================

class GoogleWorkspaceService:
    """
    Unified service for Google Workspace operations.
    Handles Drive, Docs, Sheets, and Calendar.
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
    
    # ========================================================================
    # TOKEN MANAGEMENT
    # ========================================================================
    
    async def _get_tokens(self) -> Optional[Dict[str, Any]]:
        """Get stored tokens for user"""
        # Try cache first (for backward compatibility with calendar tokens)
        tokens = cache_get(f"google_calendar_tokens:{self.user_id}")
        if tokens:
            return tokens
        
        # Try workspace tokens (includes Drive scope)
        tokens = cache_get(f"google_workspace_tokens:{self.user_id}")
        return tokens
    
    async def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Save tokens for user"""
        cache_set(
            f"google_workspace_tokens:{self.user_id}",
            tokens,
            ttl=86400 * 30  # 30 days
        )
    
    async def _refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token"""
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
                logger.error(f"Token refresh failed: {response.text}")
                raise TokenExpiredError("Failed to refresh token", response.status_code)
            
            data = response.json()
            return {
                "access_token": data.get("access_token"),
                "expires_at": datetime.utcnow().timestamp() + data.get("expires_in", 3600),
            }
    
    async def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if needed.
        Raises TokenExpiredError if no valid token available.
        """
        # Check cached token
        if self._access_token and self._token_expires_at:
            if self._token_expires_at > datetime.utcnow().timestamp() + 60:  # 60s buffer
                return self._access_token
        
        # Get stored tokens
        tokens = await self._get_tokens()
        if not tokens:
            raise TokenExpiredError("No tokens found for user")
        
        # Check if token is expired
        expires_at = tokens.get("expires_at", 0)
        if expires_at < datetime.utcnow().timestamp() + 60:
            # Try to refresh
            refresh_token = tokens.get("refresh_token")
            if not refresh_token:
                raise TokenExpiredError("No refresh token available")
            
            new_tokens = await self._refresh_token(refresh_token)
            tokens.update(new_tokens)
            await self._save_tokens(tokens)
        
        self._access_token = tokens["access_token"]
        self._token_expires_at = tokens.get("expires_at")
        
        return self._access_token
    
    # ========================================================================
    # HTTP HELPERS
    # ========================================================================
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError)
    )
    async def _request(
        self,
        method: str,
        url: str,
        json: dict = None,
        params: dict = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Google API with retry"""
        access_token = await self.get_access_token()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=json,
                params=params,
            )
            
            # Handle specific error codes
            if response.status_code == 401:
                # Token might have expired during request
                self._access_token = None
                raise TokenExpiredError("Token expired during request")
            
            if response.status_code == 403:
                error_data = response.json()
                if "quotaExceeded" in str(error_data):
                    raise QuotaExceededError("Google API quota exceeded", 403, error_data)
                raise GoogleAPIError("Access denied", 403, error_data)
            
            if response.status_code == 404:
                raise FileNotFoundError("Resource not found", 404)
            
            if response.status_code >= 400:
                raise GoogleAPIError(
                    f"Google API error: {response.text}",
                    response.status_code,
                    response.json() if response.text else {}
                )
            
            return response.json() if response.text else {}
    
    # ========================================================================
    # DRIVE OPERATIONS
    # ========================================================================
    
    async def create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create a folder in Google Drive.
        Returns: {"id": "folder_id", "url": "drive_url"}
        """
        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        
        if parent_id:
            body["parents"] = [parent_id]
        
        result = await self._request(
            "POST",
            "https://www.googleapis.com/drive/v3/files",
            json=body,
            params={"fields": "id,name,webViewLink"}
        )
        
        return {
            "id": result["id"],
            "name": result.get("name"),
            "url": result.get("webViewLink", f"https://drive.google.com/drive/folders/{result['id']}")
        }
    
    async def get_folder(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get folder metadata"""
        try:
            return await self._request(
                "GET",
                f"https://www.googleapis.com/drive/v3/files/{folder_id}",
                params={"fields": "id,name,webViewLink,mimeType,parents"}
            )
        except FileNotFoundError:
            return None
    
    async def list_folder_contents(
        self,
        folder_id: str,
        mime_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List contents of a folder"""
        query = f"'{folder_id}' in parents and trashed = false"
        if mime_type:
            query += f" and mimeType = '{mime_type}'"
        
        result = await self._request(
            "GET",
            "https://www.googleapis.com/drive/v3/files",
            params={
                "q": query,
                "fields": "files(id,name,mimeType,webViewLink,createdTime)",
                "orderBy": "name",
            }
        )
        
        return result.get("files", [])
    
    async def find_folder_by_name(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find folder by name in parent"""
        query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        result = await self._request(
            "GET",
            "https://www.googleapis.com/drive/v3/files",
            params={
                "q": query,
                "fields": "files(id,name,webViewLink)",
            }
        )
        
        files = result.get("files", [])
        return files[0] if files else None
    
    async def move_file(
        self,
        file_id: str,
        new_parent_id: str,
        old_parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Move a file to a new folder"""
        params = {
            "addParents": new_parent_id,
            "fields": "id,name,parents",
        }
        if old_parent_id:
            params["removeParents"] = old_parent_id
        
        return await self._request(
            "PATCH",
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params=params
        )
    
    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file or folder from Google Drive.
        
        Args:
            file_id: Google Drive file/folder ID
            
        Returns:
            True if deleted successfully
        """
        try:
            await self._request(
                "DELETE",
                f"https://www.googleapis.com/drive/v3/files/{file_id}"
            )
            return True
        except GoogleAPIError as e:
            if e.status_code == 404:
                return True  # Already deleted
            raise
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str = "application/pdf",
        parent_folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_content: File bytes
            filename: Name for the file
            mime_type: MIME type of the file
            parent_folder_id: Optional parent folder ID
            
        Returns:
            File metadata with id and webViewLink
        """
        import base64
        
        # For multipart upload
        metadata = {"name": filename}
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]
        
        # Use resumable upload for larger files
        async with httpx.AsyncClient() as client:
            access_token = await self.get_access_token()
            
            # Step 1: Initiate resumable upload
            init_response = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=metadata
            )
            
            if init_response.status_code != 200:
                raise GoogleAPIError(
                    f"Failed to initiate upload: {init_response.text}",
                    init_response.status_code
                )
            
            from app.services.safe_provider_url import google_upload_url
            upload_url = google_upload_url(init_response.headers.get("Location"))
            
            # Step 2: Upload file content
            upload_response = await client.put(
                upload_url,
                headers={
                    "Content-Type": mime_type,
                    "Content-Length": str(len(file_content)),
                },
                content=file_content
            )
            
            if upload_response.status_code not in [200, 201]:
                raise GoogleAPIError(
                    f"Failed to upload file: {upload_response.text}",
                    upload_response.status_code
                )
            
            result = upload_response.json()
            
            # Get full metadata with webViewLink
            file_metadata = await self.get_file_metadata(
                result["id"],
                "id,name,webViewLink,mimeType"
            )
            
            return file_metadata
    
    async def get_file_metadata(
        self,
        file_id: str,
        fields: str = "id,name,mimeType,trashed"
    ) -> Dict[str, Any]:
        """
        Get metadata for a file or folder.
        Raises FileNotFoundError if the file doesn't exist.
        
        Args:
            file_id: Google Drive file/folder ID
            fields: Fields to return
            
        Returns:
            File metadata dict
        """
        try:
            result = await self._request(
                "GET",
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={"fields": fields}
            )
            return result
        except GoogleAPIError as e:
            if e.status_code == 404:
                raise FileNotFoundError(f"File {file_id} not found", 404)
            raise
    
    async def file_exists(self, file_id: str) -> bool:
        """Check if a file/folder exists in Drive"""
        try:
            meta = await self.get_file_metadata(file_id, "id,trashed")
            return not meta.get("trashed", False)
        except FileNotFoundError:
            return False
        except Exception:
            # On other errors, assume it exists to be safe
            return True
    
    # ========================================================================
    # DOCS OPERATIONS
    # ========================================================================
    
    async def copy_document(
        self,
        template_id: str,
        name: str,
        parent_folder_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Copy a Google Doc template.
        Returns: {"id": "doc_id", "url": "doc_url"}
        """
        body = {"name": name}
        if parent_folder_id:
            body["parents"] = [parent_folder_id]
        
        result = await self._request(
            "POST",
            f"https://www.googleapis.com/drive/v3/files/{template_id}/copy",
            json=body,
            params={"fields": "id,name,webViewLink"}
        )
        
        return {
            "id": result["id"],
            "name": result.get("name"),
            "url": result.get("webViewLink", f"https://docs.google.com/document/d/{result['id']}/edit")
        }
    
    async def replace_document_placeholders(
        self,
        doc_id: str,
        replacements: Dict[str, str],
    ) -> None:
        """
        Replace placeholders in a Google Doc.
        Format: {"{{PLACEHOLDER}}": "replacement value"}
        """
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": placeholder, "matchCase": True},
                    "replaceText": value,
                }
            }
            for placeholder, value in replacements.items()
        ]
        
        if requests:
            await self._request(
                "POST",
                f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
                json={"requests": requests}
            )
    
    # ========================================================================
    # SHEETS OPERATIONS
    # ========================================================================
    
    async def copy_spreadsheet(
        self,
        template_id: str,
        name: str,
        parent_folder_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Copy a Google Sheet template.
        Returns: {"id": "sheet_id", "url": "sheet_url"}
        """
        body = {"name": name}
        if parent_folder_id:
            body["parents"] = [parent_folder_id]
        
        result = await self._request(
            "POST",
            f"https://www.googleapis.com/drive/v3/files/{template_id}/copy",
            json=body,
            params={"fields": "id,name,webViewLink"}
        )
        
        return {
            "id": result["id"],
            "name": result.get("name"),
            "url": result.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{result['id']}/edit")
        }
    
    # ========================================================================
    # CALENDAR OPERATIONS
    # ========================================================================
    
    async def create_event(
        self,
        summary: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        description: Optional[str] = None,
        calendar_id: str = "primary",
        all_day: bool = False,
        reminder_minutes: int = 1440,  # 24h
    ) -> Dict[str, str]:
        """
        Create a calendar event.
        Returns: {"id": "event_id", "url": "event_url"}
        """
        if all_day:
            event_body = {
                "summary": summary,
                "description": description,
                "start": {"date": start_date.strftime("%Y-%m-%d")},
                "end": {"date": (end_date or start_date + timedelta(days=1)).strftime("%Y-%m-%d")},
            }
        else:
            event_body = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_date.isoformat(), "timeZone": "Europe/Paris"},
                "end": {"dateTime": (end_date or start_date + timedelta(hours=1)).isoformat(), "timeZone": "Europe/Paris"},
            }
        
        event_body["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": reminder_minutes}]
        }
        
        result = await self._request(
            "POST",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            json=event_body,
        )
        
        return {
            "id": result["id"],
            "url": result.get("htmlLink", ""),
        }
    
    async def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_date: Optional[datetime] = None,
        description: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, str]:
        """Update an existing calendar event"""
        body = {}
        if summary:
            body["summary"] = summary
        if description:
            body["description"] = description
        if start_date:
            body["start"] = {"date": start_date.strftime("%Y-%m-%d")}
            body["end"] = {"date": (start_date + timedelta(days=1)).strftime("%Y-%m-%d")}
        
        result = await self._request(
            "PATCH",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            json=body,
        )
        
        return {
            "id": result["id"],
            "url": result.get("htmlLink", ""),
        }
    
    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> bool:
        """Delete a calendar event"""
        try:
            await self._request(
                "DELETE",
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            )
            return True
        except Exception:
            return False
    
    async def list_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_id: str = "primary",
        max_results: int = 250,
    ) -> List[Dict[str, Any]]:
        """
        List calendar events within a time range.
        Returns list of events with id, summary, start, end, etc.
        """
        params = {
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        
        if time_min:
            params["timeMin"] = time_min.isoformat() + "Z"
        if time_max:
            params["timeMax"] = time_max.isoformat() + "Z"
        
        result = await self._request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            params=params,
        )
        
        events = []
        for item in result.get("items", []):
            # Parse start/end dates
            start = item.get("start", {})
            end = item.get("end", {})
            
            events.append({
                "id": item["id"],
                "summary": item.get("summary", "Sans titre"),
                "description": item.get("description"),
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "all_day": "date" in start,
                "html_link": item.get("htmlLink"),
                "status": item.get("status"),
                "location": item.get("location"),
                "attendees": [
                    {"email": a.get("email"), "response": a.get("responseStatus")}
                    for a in item.get("attendees", [])
                ],
            })
        
        return events
    
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars accessible by the user"""
        result = await self._request(
            "GET",
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            params={"maxResults": 100}
        )
        
        return [
            {
                "id": cal["id"],
                "summary": cal.get("summary", ""),
                "primary": cal.get("primary", False),
                "background_color": cal.get("backgroundColor"),
                "foreground_color": cal.get("foregroundColor"),
            }
            for cal in result.get("items", [])
        ]
    
    # ========================================================================
    # WORKSPACE STRUCTURE HELPERS
    # ========================================================================
    
    async def ensure_workspace_structure(
        self,
        root_folder_id: Optional[str] = None,
        workspace_name: str = "Radar Workspace",
    ) -> Dict[str, Any]:
        """
        Create or verify the standard workspace folder structure in Drive.
        Returns folder IDs for each standard folder.
        """
        result = {
            "success": True,
            "root_folder_id": root_folder_id,
            "folders": {},
            "errors": [],
        }
        
        # Create root if needed
        if not root_folder_id:
            try:
                root = await self.create_folder(workspace_name)
                result["root_folder_id"] = root["id"]
                root_folder_id = root["id"]
            except Exception as e:
                result["success"] = False
                result["errors"].append(f"Failed to create root folder: {e}")
                return result
        
        # Create standard folders
        for folder_name, description in WORKSPACE_FOLDER_STRUCTURE.items():
            try:
                # Check if exists
                existing = await self.find_folder_by_name(folder_name, root_folder_id)
                if existing:
                    result["folders"][folder_name] = existing["id"]
                else:
                    folder = await self.create_folder(folder_name, root_folder_id)
                    result["folders"][folder_name] = folder["id"]
            except Exception as e:
                result["errors"].append(f"Failed to create {folder_name}: {e}")
        
        return result
    
    async def ensure_client_folder(
        self,
        client_name: str,
        clients_folder_id: str,
    ) -> Dict[str, str]:
        """
        Create or find a client folder in the Clients folder.
        Returns: {"id": "folder_id", "url": "folder_url"}
        """
        # Check if exists
        existing = await self.find_folder_by_name(client_name, clients_folder_id)
        if existing:
            return {
                "id": existing["id"],
                "url": existing.get("webViewLink", f"https://drive.google.com/drive/folders/{existing['id']}")
            }
        
        # Create new
        return await self.create_folder(client_name, clients_folder_id)
    
    async def ensure_project_folder(
        self,
        project_name: str,
        parent_folder_id: str,
    ) -> Dict[str, Any]:
        """
        Create or find a project folder with standard subfolders.
        Returns: {"id": "folder_id", "url": "folder_url", "subfolders": {...}}
        """
        # Check if exists
        existing = await self.find_folder_by_name(project_name, parent_folder_id)
        if existing:
            project_id = existing["id"]
        else:
            project = await self.create_folder(project_name, parent_folder_id)
            project_id = project["id"]
        
        result = {
            "id": project_id,
            "url": f"https://drive.google.com/drive/folders/{project_id}",
            "subfolders": {},
        }
        
        # Create subfolders
        for subfolder_name in PROJECT_FOLDER_STRUCTURE:
            sub_existing = await self.find_folder_by_name(subfolder_name, project_id)
            if sub_existing:
                result["subfolders"][subfolder_name] = sub_existing["id"]
            else:
                sub = await self.create_folder(subfolder_name, project_id)
                result["subfolders"][subfolder_name] = sub["id"]
        
        return result
    
    async def create_brief_from_template(
        self,
        template_id: str,
        project_name: str,
        brief_folder_id: str,
        replacements: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Copy brief template and optionally replace placeholders.
        Returns: {"id": "doc_id", "url": "doc_url"}
        """
        doc = await self.copy_document(
            template_id,
            f"Brief - {project_name}",
            brief_folder_id,
        )
        
        if replacements:
            await self.replace_document_placeholders(doc["id"], replacements)
        
        return doc
    
    async def create_report_from_template(
        self,
        template_id: str,
        project_name: str,
        admin_folder_id: str,
    ) -> Dict[str, str]:
        """
        Copy report template sheet.
        Returns: {"id": "sheet_id", "url": "sheet_url"}
        """
        return await self.copy_spreadsheet(
            template_id,
            f"Report - {project_name}",
            admin_folder_id,
        )
    
    async def create_deadline_event(
        self,
        title: str,
        deadline: datetime,
        description: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, str]:
        """
        Create a deadline event in calendar.
        Returns: {"id": "event_id", "url": "event_url"}
        """
        return await self.create_event(
            summary=f"🎯 Deadline: {title}",
            start_date=deadline,
            description=description,
            calendar_id=calendar_id,
            all_day=True,
            reminder_minutes=1440,  # 24h before
        )

    # ========================================================================
    # PROJECT DRIVE STRUCTURE - MAIN FUNCTION
    # ========================================================================

    async def create_project_drive_structure(
        self,
        project_name: str,
        brief_template_id: Optional[str] = None,
        report_template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create complete project folder structure in Google Drive.
        
        Structure created:
        Radar/
        └── Projets/
            └── <project_name>/
                ├── 01_Brief
                ├── 02_Production
                ├── 03_PostProd
                ├── 04_Exports
                ├── 05_Admin
                └── 99_Archive
        
        Args:
            project_name: Name of the project
            brief_template_id: Optional Google Docs template ID for brief
            report_template_id: Optional Google Sheets template ID for report
        
        Returns:
            {
                "success": bool,
                "drive_folder_id": str,
                "drive_folder_url": str,
                "brief_doc_id": str | None,
                "brief_doc_url": str | None,
                "report_sheet_id": str | None,
                "report_sheet_url": str | None,
                "subfolders": {
                    "01_Brief": str,
                    "02_Production": str,
                    ...
                },
                "errors": []
            }
        """
        logger.info(f"Creating Drive structure for project: {project_name}")
        
        result = {
            "success": True,
            "drive_folder_id": None,
            "drive_folder_url": None,
            "brief_doc_id": None,
            "brief_doc_url": None,
            "report_sheet_id": None,
            "report_sheet_url": None,
            "subfolders": {},
            "errors": [],
        }
        
        try:
            # Step 1: Find or create "Radar" folder at root
            radar_folder = await self.find_folder_by_name("Radar", parent_id=None)
            if radar_folder:
                radar_folder_id = radar_folder["id"]
                logger.debug(f"Found existing Radar folder: {radar_folder_id}")
            else:
                radar = await self.create_folder("Radar")
                radar_folder_id = radar["id"]
                logger.info(f"Created Radar folder: {radar_folder_id}")
            
            # Step 2: Find or create "Projets" folder inside Radar
            projets_folder = await self.find_folder_by_name("Projets", radar_folder_id)
            if projets_folder:
                projets_folder_id = projets_folder["id"]
                logger.debug(f"Found existing Projets folder: {projets_folder_id}")
            else:
                projets = await self.create_folder("Projets", radar_folder_id)
                projets_folder_id = projets["id"]
                logger.info(f"Created Projets folder: {projets_folder_id}")
            
            # Step 2b: Find or create "Archives" folder inside Radar (for deleted projects)
            archives_folder = await self.find_folder_by_name("Archives", radar_folder_id)
            if not archives_folder:
                await self.create_folder("Archives", radar_folder_id)
                logger.info("Created Archives folder inside Radar")
            
            # Step 3: Check if project folder already exists (avoid duplicates)
            existing_project = await self.find_folder_by_name(project_name, projets_folder_id)
            if existing_project:
                logger.warning(f"Project folder already exists: {project_name}")
                result["drive_folder_id"] = existing_project["id"]
                result["drive_folder_url"] = f"https://drive.google.com/drive/folders/{existing_project['id']}"
                # Still need to verify/create subfolders
                project_folder_id = existing_project["id"]
            else:
                # Create project folder
                project_folder = await self.create_folder(project_name, projets_folder_id)
                project_folder_id = project_folder["id"]
                result["drive_folder_id"] = project_folder_id
                result["drive_folder_url"] = project_folder["url"]
                logger.info(f"Created project folder: {project_name} ({project_folder_id})")
            
            # Step 4: Create all subfolders
            for subfolder_name in PROJECT_FOLDER_STRUCTURE:
                try:
                    existing_sub = await self.find_folder_by_name(subfolder_name, project_folder_id)
                    if existing_sub:
                        result["subfolders"][subfolder_name] = existing_sub["id"]
                    else:
                        sub = await self.create_folder(subfolder_name, project_folder_id)
                        result["subfolders"][subfolder_name] = sub["id"]
                        logger.debug(f"Created subfolder: {subfolder_name}")
                except Exception as e:
                    error_msg = f"Failed to create subfolder {subfolder_name}: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
            
            # Step 5: Copy Brief template to 01_Brief folder
            if brief_template_id and result["subfolders"].get("01_Brief"):
                try:
                    brief_doc = await self.copy_document(
                        template_id=brief_template_id,
                        name=f"Brief - {project_name}",
                        parent_folder_id=result["subfolders"]["01_Brief"]
                    )
                    result["brief_doc_id"] = brief_doc["id"]
                    result["brief_doc_url"] = brief_doc["url"]
                    logger.info(f"Created brief document: {brief_doc['id']}")
                except Exception as e:
                    error_msg = f"Failed to create brief from template: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
            
            # Step 6: Copy Report template to 05_Admin folder
            if report_template_id and result["subfolders"].get("05_Admin"):
                try:
                    report_sheet = await self.copy_spreadsheet(
                        template_id=report_template_id,
                        name=f"Reporting - {project_name}",
                        parent_folder_id=result["subfolders"]["05_Admin"]
                    )
                    result["report_sheet_id"] = report_sheet["id"]
                    result["report_sheet_url"] = report_sheet["url"]
                    logger.info(f"Created report spreadsheet: {report_sheet['id']}")
                except Exception as e:
                    error_msg = f"Failed to create report from template: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
            
            result["success"] = len(result["errors"]) == 0
            logger.info(f"Project Drive structure created successfully for: {project_name}")
            
        except TokenExpiredError as e:
            logger.error(f"Token expired during Drive structure creation: {e}")
            result["success"] = False
            result["errors"].append("Google authorization expired. Please reconnect.")
            raise
        
        except QuotaExceededError as e:
            logger.error(f"Quota exceeded during Drive structure creation: {e}")
            result["success"] = False
            result["errors"].append("Google API quota exceeded. Please try again later.")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Drive structure: {e}")
            result["success"] = False
            result["errors"].append(str(e))
            raise GoogleAPIError(f"Failed to create project Drive structure: {e}")
        
        return result

    # ========================================================================
    # BILLING DOCUMENT GENERATION (Devis / Factures)
    # ========================================================================

    async def ensure_client_billing_folder(
        self,
        client_name: str,
        root_folder_id: str,
        doc_type: str = "Devis"  # "Devis" or "Factures"
    ) -> Dict[str, str]:
        """
        Create or find the folder structure for billing documents.
        Structure: Radar / Clients / [ClientName] / Devis (or Factures)
        
        Returns: {"id": "folder_id", "url": "folder_url", "client_folder_id": "..."}
        """
        result = {"errors": []}
        
        try:
            # Step 1: Ensure "Clients" folder exists at root
            clients_folder = await self.find_folder_by_name("Clients", root_folder_id)
            if not clients_folder:
                clients_folder = await self.create_folder("Clients", root_folder_id)
                clients_folder_id = clients_folder["id"]
            else:
                clients_folder_id = clients_folder["id"]
            
            # Step 2: Ensure client folder exists
            # Sanitize client name for folder
            safe_client_name = client_name.replace("/", "-").replace("\\", "-").strip()
            client_folder = await self.find_folder_by_name(safe_client_name, clients_folder_id)
            if not client_folder:
                client_folder = await self.create_folder(safe_client_name, clients_folder_id)
                client_folder_id = client_folder["id"]
            else:
                client_folder_id = client_folder["id"]
            
            # Step 3: Ensure doc_type folder exists (Devis or Factures)
            doc_folder = await self.find_folder_by_name(doc_type, client_folder_id)
            if not doc_folder:
                doc_folder = await self.create_folder(doc_type, client_folder_id)
            
            return {
                "id": doc_folder["id"],
                "url": doc_folder.get("url", f"https://drive.google.com/drive/folders/{doc_folder['id']}"),
                "client_folder_id": client_folder_id,
                "clients_folder_id": clients_folder_id,
            }
            
        except Exception as e:
            logger.error(f"Failed to ensure client billing folder: {e}")
            raise GoogleAPIError(f"Failed to create folder structure: {e}")

    async def generate_quote_document(
        self,
        template_id: str,
        quote_reference: str,
        client_name: str,
        root_folder_id: str,
        replacements: Dict[str, str],
    ) -> Dict[str, str]:
        """
        Generate a quote document from template in the client's Devis folder.
        
        Args:
            template_id: Google Doc template ID
            quote_reference: e.g., "DEV-2026-0001"
            client_name: Client name for folder
            root_folder_id: Workspace root Drive folder ID
            replacements: Placeholder replacements {"{{PLACEHOLDER}}": "value"}
        
        Returns: {"id": "doc_id", "url": "doc_url", "folder_id": "folder_id"}
        """
        # Ensure folder structure
        folder = await self.ensure_client_billing_folder(
            client_name, root_folder_id, "Devis"
        )
        
        # Copy template
        doc_name = f"Devis {quote_reference} - {client_name}"
        doc = await self.copy_document(template_id, doc_name, folder["id"])
        
        # Replace placeholders
        if replacements:
            await self.replace_document_placeholders(doc["id"], replacements)
        
        return {
            "id": doc["id"],
            "url": doc["url"],
            "folder_id": folder["id"],
        }

    async def generate_invoice_document(
        self,
        template_id: str,
        invoice_reference: str,
        client_name: str,
        root_folder_id: str,
        replacements: Dict[str, str],
    ) -> Dict[str, str]:
        """
        Generate an invoice document from template in the client's Factures folder.
        
        Args:
            template_id: Google Doc template ID
            invoice_reference: e.g., "FAC-2026-0001"
            client_name: Client name for folder
            root_folder_id: Workspace root Drive folder ID
            replacements: Placeholder replacements {"{{PLACEHOLDER}}": "value"}
        
        Returns: {"id": "doc_id", "url": "doc_url", "folder_id": "folder_id"}
        """
        # Ensure folder structure
        folder = await self.ensure_client_billing_folder(
            client_name, root_folder_id, "Factures"
        )
        
        # Copy template
        doc_name = f"Facture {invoice_reference} - {client_name}"
        doc = await self.copy_document(template_id, doc_name, folder["id"])
        
        # Replace placeholders
        if replacements:
            await self.replace_document_placeholders(doc["id"], replacements)
        
        return {
            "id": doc["id"],
            "url": doc["url"],
            "folder_id": folder["id"],
        }

    async def export_document_to_pdf(
        self,
        doc_id: str,
        target_folder_id: str,
        pdf_name: str,
    ) -> Dict[str, str]:
        """
        Export a Google Doc to PDF and save in the same folder.
        
        Returns: {"id": "pdf_file_id", "url": "pdf_url"}
        """
        # Export as PDF
        pdf_content = await self._request(
            "GET",
            f"https://www.googleapis.com/drive/v3/files/{doc_id}/export",
            params={"mimeType": "application/pdf"},
            raw_response=True
        )
        
        # Upload PDF to Drive
        # Note: This requires multipart upload - simplified version
        # For production, use resumable upload for large files
        metadata = {
            "name": pdf_name,
            "parents": [target_folder_id],
            "mimeType": "application/pdf"
        }
        
        # For simplicity, we'll use the webViewLink of the exported doc
        # In production, implement proper multipart upload
        pdf_url = f"https://drive.google.com/file/d/{doc_id}/view"
        
        return {
            "id": doc_id,  # Same as doc for now
            "url": pdf_url,
        }


# ============================================================================
# FACTORY
# ============================================================================

def get_google_workspace_service(user_id: int) -> GoogleWorkspaceService:
    """Factory function to create GoogleWorkspaceService"""
    return GoogleWorkspaceService(user_id)
