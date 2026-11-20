"""
Google Drive API - Drive/Docs/Sheets operations for entities
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, Form, UploadFile, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.workspace import Workspace
from app.db.models.agency import Client, Project, Deliverable
from app.api.deps import get_current_user, get_current_workspace
from app.core import integration_oauth
from app.api.workspace import _user_has_workspace_access
from app.services.google_workspace import get_google_workspace_service, GoogleAPIError, TokenExpiredError, GOOGLE_WORKSPACE_SCOPES
from app.core.config import settings
from app.core.cache import cache_get, cache_set

router = APIRouter(prefix="/drive", tags=["google-drive"])

callback_router = APIRouter(prefix="/drive", tags=["google-drive"])


# ============================================================================
# OAUTH FOR GOOGLE WORKSPACE (Drive, Docs, Sheets)
# ============================================================================

class AuthInitResponse(BaseModel):
    auth_url: str
    state: str


class ConnectionStatus(BaseModel):
    connected: bool
    email: Optional[str] = None
    scopes: Optional[list] = None


@router.get("/auth/init", response_model=AuthInitResponse)
async def init_google_workspace_oauth(
    request: Request,
    db: Session = Depends(get_db),
    workspace=Depends(get_current_workspace),
    redirect: Optional[str] = Query(None, description="Path to redirect after auth"),
    current_user: User = Depends(get_current_user),
):
    """
    Initialize Google Workspace OAuth flow with Drive/Docs/Sheets scopes.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    
    state = integration_oauth.issue(db, current_user, workspace, request, 'drive', redirect)

    redirect_uri = f"{settings.backend_url}/api/v1/drive/auth/callback"
    
    # Include email and profile scopes too
    scopes = GOOGLE_WORKSPACE_SCOPES + [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return AuthInitResponse(auth_url=auth_url, state=state)


@callback_router.get("/auth/callback")
async def google_workspace_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    Handle Google Workspace OAuth callback.
    Exchanges code for tokens and stores them for Drive/Docs/Sheets access.
    """
    import httpx
    
    stored_state = integration_oauth.consume(db, state, 'drive')
    user_id = stored_state['user_id']
    redirect_path = integration_oauth.safe_redirect(stored_state.get('redirect'))
    redirect_uri = f"{settings.backend_url}/api/v1/drive/auth/callback"
    
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
        
        # Store tokens in cache
        integration_oauth.save_tokens(
            db, stored_state, f"google_workspace_tokens:{user_id}",
            {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": datetime.utcnow().timestamp() + tokens.get("expires_in", 3600),
                "email": user_info.get("email"),
                "scopes": tokens.get("scope", "").split(" "),
            },
        )
        
        # Redirect to frontend with success
        return RedirectResponse(
            url=f"{settings.frontend_url}{redirect_path}{'&' if '?' in redirect_path else '?'}google_connected=true"
        )
        
    except Exception as e:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.frontend_url}{redirect_path}{'&' if '?' in redirect_path else '?'}google_error=connection_failed"
        )


@router.get("/auth/status", response_model=ConnectionStatus)
async def get_workspace_connection_status(
    current_user: User = Depends(get_current_user),
):
    """Check if user has connected Google Workspace with Drive/Docs/Sheets scopes"""
    tokens = cache_get(f"google_workspace_tokens:{current_user.id}")
    
    if not tokens:
        return ConnectionStatus(connected=False)
    
    # Check if token is expired
    if tokens.get("expires_at", 0) < datetime.utcnow().timestamp():
        # Token expired - check if we have refresh token
        if not tokens.get("refresh_token"):
            return ConnectionStatus(connected=False)
        # Could refresh here, but for now just return as connected since we have refresh token
    
    return ConnectionStatus(
        connected=True,
        email=tokens.get("email"),
        scopes=tokens.get("scopes", [])
    )


@router.delete("/auth/disconnect")
async def disconnect_google_workspace(
    current_user: User = Depends(get_current_user),
):
    """Disconnect Google Workspace integration"""
    from app.core.cache import cache_delete
    cache_delete(f"google_workspace_tokens:{current_user.id}")
    return {"success": True, "message": "Google Workspace disconnected"}


# ============================================================================
# SCHEMAS
# ============================================================================

class FolderResponse(BaseModel):
    id: str
    url: str
    name: Optional[str] = None


class DocResponse(BaseModel):
    id: str
    url: str
    name: Optional[str] = None


class CreateFolderRequest(BaseModel):
    name: Optional[str] = None  # Use entity name if not provided


class CreateDocRequest(BaseModel):
    name: Optional[str] = None
    template_id: Optional[str] = None  # Use workspace template if not provided
    replacements: Optional[dict] = None  # {"{{PLACEHOLDER}}": "value"}


# ============================================================================
# UPLOAD TOKEN FOR DIRECT BROWSER UPLOAD
# ============================================================================

class UploadTokenResponse(BaseModel):
    access_token: str
    expires_in: int


class UploadFileResponse(BaseModel):
    id: str
    name: str
    web_view_link: str
    mime_type: str


@router.get("/upload-token", response_model=UploadTokenResponse)
async def get_upload_token(
    current_user: User = Depends(get_current_user),
):
    """
    Get a valid access token for direct browser upload to Google Drive.
    The frontend will use this token for resumable upload.
    """
    try:
        service = get_google_workspace_service(current_user.id)
        access_token = await service.get_access_token()
        
        # Token expires in ~1 hour, but we return a safe estimate
        return UploadTokenResponse(
            access_token=access_token,
            expires_in=3500  # ~58 minutes
        )
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required. Please reconnect.")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/upload", response_model=UploadFileResponse)
async def upload_file_to_drive(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    file_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file to Google Drive (proxied through backend).
    Use this if direct browser upload fails due to CORS.
    """
    import httpx
    from app.core.advanced_security import validate_file_upload, sanitize_filename
    
    try:
        service = get_google_workspace_service(current_user.id)
        access_token = await service.get_access_token()
        
        # Read file content
        content = await file.read(50 * 1024 * 1024 + 1)
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(413, "Le fichier dépasse 50 Mo.")
        final_name = sanitize_filename(file_name or file.filename)
        
        # ============ SECURITY: Validate file upload ============
        is_valid, error_msg = validate_file_upload(final_name, content, max_size_mb=50)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        # ========================================================
        
        # Metadata
        metadata = {
            "name": final_name,
            "parents": [folder_id]
        }
        
        # Use multipart upload for simplicity
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create multipart body
            from httpx._multipart import MultipartStream
            
            # Simple upload (for files < 5MB) 
            # For larger files, use resumable upload
            if len(content) < 5 * 1024 * 1024:
                # Simple multipart upload
                import json
                boundary = "radar_upload_boundary"
                
                body = (
                    f'--{boundary}\r\n'
                    f'Content-Type: application/json; charset=UTF-8\r\n\r\n'
                    f'{json.dumps(metadata)}\r\n'
                    f'--{boundary}\r\n'
                    f'Content-Type: {file.content_type or "application/octet-stream"}\r\n\r\n'
                ).encode('utf-8') + content + f'\r\n--{boundary}--'.encode('utf-8')
                
                response = await client.post(
                    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink,mimeType",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": f"multipart/related; boundary={boundary}",
                    },
                    content=body
                )
            else:
                # Resumable upload for larger files
                # Step 1: Initiate resumable session
                init_response = await client.post(
                    "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "X-Upload-Content-Type": file.content_type or "application/octet-stream",
                        "X-Upload-Content-Length": str(len(content)),
                    },
                    json=metadata
                )
                
                if init_response.status_code != 200:
                    raise GoogleAPIError(f"Failed to initiate upload: {init_response.text}", init_response.status_code)
                
                upload_url = init_response.headers.get("Location")
                
                from app.services.safe_provider_url import google_upload_url
                upload_url = google_upload_url(upload_url)
                # Step 2: Upload content
                response = await client.put(
                    upload_url,
                    headers={
                        "Content-Type": file.content_type or "application/octet-stream",
                        "Content-Length": str(len(content)),
                    },
                    content=content,
                    params={"fields": "id,name,webViewLink,mimeType"}
                )
            
            if response.status_code not in [200, 201]:
                raise GoogleAPIError(f"Upload failed: {response.text}", response.status_code)
            
            result = response.json()
            
            return UploadFileResponse(
                id=result["id"],
                name=result["name"],
                web_view_link=result.get("webViewLink", f"https://drive.google.com/file/d/{result['id']}/view"),
                mime_type=result.get("mimeType", "application/octet-stream")
            )
            
    except HTTPException:
        raise
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required")
    except GoogleAPIError as e:
        raise HTTPException(status_code=502, detail="Le transfert vers Google Drive a échoué. Réessayez ou reconnectez Google.")
    except Exception as e:
        raise HTTPException(status_code=502, detail="Le transfert vers Google Drive est temporairement indisponible.")
    finally:
        await file.close()


# ============================================================================
# CLIENT DRIVE
# ============================================================================

@router.post("/clients/{client_id}/folder", response_model=FolderResponse)
async def create_client_folder(
    client_id: int,
    data: CreateFolderRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or get Drive folder for client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client.workspace_id and not _user_has_workspace_access(db, current_user.id, client.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return existing folder if exists
    if client.drive_folder_id:
        return FolderResponse(
            id=client.drive_folder_id,
            url=f"https://drive.google.com/drive/folders/{client.drive_folder_id}",
            name=client.name
        )
    
    # Get workspace for parent folder
    workspace = None
    clients_folder_id = None
    if client.workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == client.workspace_id).first()
        if workspace and workspace.drive_root_folder_id:
            # Find or create Clients folder
            try:
                service = get_google_workspace_service(current_user.id)
                existing = await service.find_folder_by_name("Clients", workspace.drive_root_folder_id)
                if existing:
                    clients_folder_id = existing["id"]
                else:
                    folder = await service.create_folder("Clients", workspace.drive_root_folder_id)
                    clients_folder_id = folder["id"]
            except TokenExpiredError:
                raise HTTPException(status_code=401, detail="Google authorization required")
            except GoogleAPIError as e:
                raise HTTPException(status_code=e.status_code, detail=e.message)
    
    try:
        service = get_google_workspace_service(current_user.id)
        folder_name = (data and data.name) or client.name
        
        result = await service.ensure_client_folder(folder_name, clients_folder_id)
        
        # Save folder ID to client
        client.drive_folder_id = result["id"]
        db.commit()
        
        return FolderResponse(
            id=result["id"],
            url=result["url"],
            name=folder_name
        )
        
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/clients/{client_id}/folder", response_model=Optional[FolderResponse])
async def get_client_folder(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get client Drive folder info"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client.workspace_id and not _user_has_workspace_access(db, current_user.id, client.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not client.drive_folder_id:
        return None
    
    return FolderResponse(
        id=client.drive_folder_id,
        url=f"https://drive.google.com/drive/folders/{client.drive_folder_id}",
        name=client.name
    )


# ============================================================================
# PROJECT DRIVE
# ============================================================================

# ============================================================================
# PROJECT DRIVE STRUCTURE - COMPLETE FOLDER HIERARCHY
# ============================================================================

class ProjectDriveResponse(BaseModel):
    """Response for project Drive structure creation"""
    success: bool
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None
    brief_doc_id: Optional[str] = None
    brief_doc_url: Optional[str] = None
    report_sheet_id: Optional[str] = None
    report_sheet_url: Optional[str] = None
    subfolders: Optional[dict] = None
    errors: Optional[list] = None


@router.post("/projects/{project_id}/structure", response_model=ProjectDriveResponse)
async def create_project_drive_structure(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create complete Drive folder structure for project.
    
    Creates:
    Radar/
    └── Projets/
        └── <project_name>/
            ├── 01_Brief
            ├── 02_Production
            ├── 03_PostProd
            ├── 04_Exports
            ├── 05_Admin
            └── 99_Archive
    
    Also copies templates if configured:
    - Brief template (Google Doc) → 01_Brief
    - Report template (Google Sheet) → 05_Admin
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Return existing structure if folder already exists
    if project.drive_folder_id:
        return ProjectDriveResponse(
            success=True,
            drive_folder_id=project.drive_folder_id,
            drive_folder_url=f"https://drive.google.com/drive/folders/{project.drive_folder_id}",
            brief_doc_id=project.brief_doc_id,
            brief_doc_url=f"https://docs.google.com/document/d/{project.brief_doc_id}/edit" if project.brief_doc_id else None,
            report_sheet_id=project.report_sheet_id,
            report_sheet_url=f"https://docs.google.com/spreadsheets/d/{project.report_sheet_id}/edit" if project.report_sheet_id else None,
        )
    
    try:
        service = get_google_workspace_service(current_user.id)
        
        # TODO: Get templates from workspace settings
        brief_template_id = None
        report_template_id = None
        
        # Create the complete structure
        result = await service.create_project_drive_structure(
            project_name=project.name,
            brief_template_id=brief_template_id,
            report_template_id=report_template_id,
        )
        
        # Update project with IDs
        if result.get("drive_folder_id"):
            project.drive_folder_id = result["drive_folder_id"]
        if result.get("brief_doc_id"):
            project.brief_doc_id = result["brief_doc_id"]
        if result.get("report_sheet_id"):
            project.report_sheet_id = result["report_sheet_id"]
        db.commit()
        
        return ProjectDriveResponse(
            success=result["success"],
            drive_folder_id=result.get("drive_folder_id"),
            drive_folder_url=result.get("drive_folder_url"),
            brief_doc_id=result.get("brief_doc_id"),
            brief_doc_url=result.get("brief_doc_url"),
            report_sheet_id=result.get("report_sheet_id"),
            report_sheet_url=result.get("report_sheet_url"),
            subfolders=result.get("subfolders"),
            errors=result.get("errors"),
        )
        
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required. Please reconnect Google.")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/projects/{project_id}/folder", response_model=FolderResponse)
async def create_project_folder(
    project_id: int,
    data: CreateFolderRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or get Drive folder for project - redirects to full structure creation"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Return existing folder if exists
    if project.drive_folder_id:
        return FolderResponse(
            id=project.drive_folder_id,
            url=f"https://drive.google.com/drive/folders/{project.drive_folder_id}",
            name=project.name
        )
    
    try:
        service = get_google_workspace_service(current_user.id)
        
        # Use the new complete structure creation
        result = await service.create_project_drive_structure(
            project_name=project.name,
            brief_template_id=None,
            report_template_id=None,
        )
        
        # Update project with folder ID
        if result.get("drive_folder_id"):
            project.drive_folder_id = result["drive_folder_id"]
            db.commit()
        
        return FolderResponse(
            id=result["drive_folder_id"],
            url=result["drive_folder_url"],
            name=project.name
        )
        
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/projects/{project_id}/folder", response_model=Optional[FolderResponse])
async def get_project_folder(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project Drive folder info"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.workspace_id and not _user_has_workspace_access(db, current_user.id, project.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not project.drive_folder_id:
        return None
    
    return FolderResponse(
        id=project.drive_folder_id,
        url=f"https://drive.google.com/drive/folders/{project.drive_folder_id}",
        name=project.name
    )


# ============================================================================
# PROJECT BRIEF (Google Doc)
# ============================================================================

@router.post("/projects/{project_id}/brief", response_model=DocResponse)
async def create_project_brief(
    project_id: int,
    data: CreateDocRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create brief document from template for project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.workspace_id and not _user_has_workspace_access(db, current_user.id, project.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return existing brief if exists
    if project.brief_doc_id:
        return DocResponse(
            id=project.brief_doc_id,
            url=f"https://docs.google.com/document/d/{project.brief_doc_id}/edit",
            name=f"Brief - {project.name}"
        )
    
    # Get template ID
    template_id = data.template_id if data else None
    if not template_id and project.workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == project.workspace_id).first()
        if workspace:
            template_id = workspace.brief_template_doc_id
    
    if not template_id:
        raise HTTPException(
            status_code=400,
            detail="No template specified and workspace has no brief template configured"
        )
    
    # Get target folder (Brief subfolder)
    target_folder = None
    if project.drive_folder_id:
        try:
            service = get_google_workspace_service(current_user.id)
            brief_folder = await service.find_folder_by_name("Brief", project.drive_folder_id)
            if brief_folder:
                target_folder = brief_folder["id"]
            else:
                target_folder = project.drive_folder_id
        except:
            target_folder = project.drive_folder_id
    
    try:
        service = get_google_workspace_service(current_user.id)
        
        # Default replacements
        replacements = data.replacements if data else {}
        if not replacements:
            replacements = {
                "{{PROJECT_NAME}}": project.name,
                "{{CLIENT_NAME}}": project.client.name if project.client else "",
                "{{DATE}}": datetime.utcnow().strftime("%d/%m/%Y"),
                "{{DEADLINE}}": project.deadline.strftime("%d/%m/%Y") if project.deadline else "À définir",
            }
        
        result = await service.create_brief_from_template(
            template_id=template_id,
            project_name=project.name,
            brief_folder_id=target_folder,
            replacements=replacements,
        )
        
        # Save doc ID to project
        project.brief_doc_id = result["id"]
        db.commit()
        
        return DocResponse(
            id=result["id"],
            url=result["url"],
            name=result.get("name", f"Brief - {project.name}")
        )
        
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/projects/{project_id}/brief", response_model=Optional[DocResponse])
async def get_project_brief(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project brief document info"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.workspace_id and not _user_has_workspace_access(db, current_user.id, project.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not project.brief_doc_id:
        return None
    
    return DocResponse(
        id=project.brief_doc_id,
        url=f"https://docs.google.com/document/d/{project.brief_doc_id}/edit",
        name=f"Brief - {project.name}"
    )


# ============================================================================
# PROJECT REPORT (Google Sheet)
# ============================================================================

@router.post("/projects/{project_id}/report", response_model=DocResponse)
async def create_project_report(
    project_id: int,
    data: CreateDocRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create report spreadsheet from template for project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.workspace_id and not _user_has_workspace_access(db, current_user.id, project.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return existing report if exists
    if project.report_sheet_id:
        return DocResponse(
            id=project.report_sheet_id,
            url=f"https://docs.google.com/spreadsheets/d/{project.report_sheet_id}/edit",
            name=f"Report - {project.name}"
        )
    
    # Get template ID
    template_id = data.template_id if data else None
    if not template_id and project.workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == project.workspace_id).first()
        if workspace:
            template_id = workspace.report_template_sheet_id
    
    if not template_id:
        raise HTTPException(
            status_code=400,
            detail="No template specified and workspace has no report template configured"
        )
    
    # Get target folder (Admin subfolder)
    target_folder = None
    if project.drive_folder_id:
        try:
            service = get_google_workspace_service(current_user.id)
            admin_folder = await service.find_folder_by_name("Admin", project.drive_folder_id)
            if admin_folder:
                target_folder = admin_folder["id"]
            else:
                target_folder = project.drive_folder_id
        except:
            target_folder = project.drive_folder_id
    
    try:
        service = get_google_workspace_service(current_user.id)
        
        result = await service.create_report_from_template(
            template_id=template_id,
            project_name=project.name,
            admin_folder_id=target_folder,
        )
        
        # Save sheet ID to project
        project.report_sheet_id = result["id"]
        db.commit()
        
        return DocResponse(
            id=result["id"],
            url=result["url"],
            name=result.get("name", f"Report - {project.name}")
        )
        
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/projects/{project_id}/report", response_model=Optional[DocResponse])
async def get_project_report(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project report sheet info"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.workspace_id and not _user_has_workspace_access(db, current_user.id, project.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not project.report_sheet_id:
        return None
    
    return DocResponse(
        id=project.report_sheet_id,
        url=f"https://docs.google.com/spreadsheets/d/{project.report_sheet_id}/edit",
        name=f"Report - {project.name}"
    )


# ============================================================================
# CALENDAR EVENTS
# ============================================================================

@router.post("/projects/{project_id}/deadline-event")
async def create_project_deadline_event(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create calendar event for project deadline"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.workspace_id and not _user_has_workspace_access(db, current_user.id, project.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not project.deadline:
        raise HTTPException(status_code=400, detail="Project has no deadline")
    
    # Return existing event if exists
    if project.calendar_event_id:
        return {
            "id": project.calendar_event_id,
            "message": "Calendar event already exists"
        }
    
    # Get calendar ID from workspace
    calendar_id = "primary"
    if project.workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == project.workspace_id).first()
        if workspace and workspace.calendar_id:
            calendar_id = workspace.calendar_id
    
    try:
        service = get_google_workspace_service(current_user.id)
        
        description = f"Deadline projet: {project.name}"
        if project.client:
            description += f"\nClient: {project.client.name}"
        
        result = await service.create_deadline_event(
            title=project.name,
            deadline=project.deadline,
            description=description,
            calendar_id=calendar_id,
        )
        
        # Save event ID to project
        project.calendar_event_id = result["id"]
        db.commit()
        
        return {
            "id": result["id"],
            "url": result["url"],
            "message": "Calendar event created"
        }
        
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/deliverables/{deliverable_id}/deadline-event")
async def create_deliverable_deadline_event(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create calendar event for deliverable deadline"""
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    project = deliverable.project
    if project.workspace_id and not _user_has_workspace_access(db, current_user.id, project.workspace_id, current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not deliverable.due_date:
        raise HTTPException(status_code=400, detail="Deliverable has no due date")
    
    # Return existing event if exists
    if deliverable.calendar_event_id:
        return {
            "id": deliverable.calendar_event_id,
            "message": "Calendar event already exists"
        }
    
    # Get calendar ID from workspace
    calendar_id = "primary"
    if project.workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == project.workspace_id).first()
        if workspace and workspace.calendar_id:
            calendar_id = workspace.calendar_id
    
    try:
        service = get_google_workspace_service(current_user.id)
        
        description = f"Livrable: {deliverable.name}\nProjet: {project.name}"
        if project.client:
            description += f"\nClient: {project.client.name}"
        
        result = await service.create_deadline_event(
            title=f"📦 {deliverable.name}",
            deadline=deliverable.due_date,
            description=description,
            calendar_id=calendar_id,
        )
        
        # Save event ID to deliverable
        deliverable.calendar_event_id = result["id"]
        db.commit()
        
        return {
            "id": result["id"],
            "url": result["url"],
            "message": "Calendar event created"
        }
        
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Google authorization required")
    except GoogleAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
