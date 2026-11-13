"""
Drive Structure Service
Handles idempotent Google Drive folder structure creation.
Creates and maintains workspace/project folder hierarchies.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.models.drive_folder_map import DriveFolderMap, DriveFolderType
from app.core.subscription import Feature, effective_features
from app.db.models.workspace import Workspace
from app.db.models.agency import Project
from app.services.google_workspace import (
    GoogleWorkspaceService,
    GoogleAPIError,
    TokenExpiredError,
    FileNotFoundError as DriveFileNotFoundError
)

logger = logging.getLogger(__name__)


# ============================================================================
# RESULT DATACLASS
# ============================================================================

@dataclass
class StructureResult:
    """Result of structure ensure operation"""
    success: bool = True
    created: List[str] = field(default_factory=list)
    restored: List[str] = field(default_factory=list)
    reused: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    folder_ids: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "created": self.created,
            "restored": self.restored,
            "reused": self.reused,
            "errors": self.errors,
            "folder_ids": self.folder_ids,
            "summary": {
                "created_count": len(self.created),
                "restored_count": len(self.restored),
                "reused_count": len(self.reused),
                "error_count": len(self.errors)
            }
        }


# ============================================================================
# FOLDER DEFINITIONS
# ============================================================================

# Core folders (always created)
CORE_FOLDERS = [
    (DriveFolderType.ROOT, "Radar", None),
    (DriveFolderType.PROJECTS_ROOT, "Projets", DriveFolderType.ROOT),
    (DriveFolderType.WORKSPACE_ROOT, "00_Workspace", DriveFolderType.ROOT),
    (DriveFolderType.WORKSPACE_RESOURCES, "01_Ressources", DriveFolderType.WORKSPACE_ROOT),
    (DriveFolderType.WORKSPACE_ARCHIVE, "99_Archive", DriveFolderType.WORKSPACE_ROOT),
]

# Templates folders (if templates enabled)
TEMPLATES_FOLDERS = [
    (DriveFolderType.TEMPLATES_ROOT, "00_Templates", DriveFolderType.WORKSPACE_ROOT),
    (DriveFolderType.TEMPLATES_DOCS, "Docs", DriveFolderType.TEMPLATES_ROOT),
    (DriveFolderType.TEMPLATES_SHEETS, "Sheets", DriveFolderType.TEMPLATES_ROOT),
]

# Business folders (if radar_business addon enabled)
BUSINESS_FOLDERS = [
    (DriveFolderType.BUSINESS_ROOT, "Business", DriveFolderType.ROOT),
    (DriveFolderType.BUSINESS_QUOTES, "Devis", DriveFolderType.BUSINESS_ROOT),
    (DriveFolderType.BUSINESS_INVOICES, "Factures", DriveFolderType.BUSINESS_ROOT),
    (DriveFolderType.BUSINESS_CREDITS, "Avoirs", DriveFolderType.BUSINESS_ROOT),
    (DriveFolderType.BUSINESS_PAYMENTS, "Paiements", DriveFolderType.BUSINESS_ROOT),
    (DriveFolderType.BUSINESS_EXPORT, "Export_Compta", DriveFolderType.BUSINESS_ROOT),
    (DriveFolderType.BUSINESS_ARCHIVE, "99_Archive", DriveFolderType.BUSINESS_ROOT),
]

# Exports folders (if analytics or intelligence pack enabled)
EXPORTS_FOLDERS = [
    (DriveFolderType.EXPORTS_ROOT, "Exports", DriveFolderType.ROOT),
    (DriveFolderType.EXPORTS_PDF, "PDF", DriveFolderType.EXPORTS_ROOT),
    (DriveFolderType.EXPORTS_CSV, "CSV", DriveFolderType.EXPORTS_ROOT),
    (DriveFolderType.EXPORTS_REPORTS, "Reports", DriveFolderType.EXPORTS_ROOT),
    (DriveFolderType.EXPORTS_ARCHIVE, "99_Archive", DriveFolderType.EXPORTS_ROOT),
]

# Discovery folders (if discovery/talents pack enabled)
DISCOVERY_FOLDERS = [
    (DriveFolderType.DISCOVERY_ROOT, "Discovery", DriveFolderType.ROOT),
    (DriveFolderType.DISCOVERY_ARTISTS, "Artistes", DriveFolderType.DISCOVERY_ROOT),
    (DriveFolderType.DISCOVERY_WATCH, "Veille", DriveFolderType.DISCOVERY_ROOT),
    (DriveFolderType.DISCOVERY_COMPARE, "Comparaisons", DriveFolderType.DISCOVERY_ROOT),
    (DriveFolderType.DISCOVERY_ARCHIVE, "99_Archive", DriveFolderType.DISCOVERY_ROOT),
]

# Data folders (if data pack enabled)
DATA_FOLDERS = [
    (DriveFolderType.DATA_ROOT, "Data", DriveFolderType.ROOT),
    (DriveFolderType.DATA_SOURCES, "Sources", DriveFolderType.DATA_ROOT),
    (DriveFolderType.DATA_LOGS, "Logs", DriveFolderType.DATA_ROOT),
    (DriveFolderType.DATA_ARCHIVE, "99_Archive", DriveFolderType.DATA_ROOT),
]

# Inbox folders (optional, always created)
INBOX_FOLDERS = [
    (DriveFolderType.INBOX_ROOT, "Inbox", DriveFolderType.ROOT),
    (DriveFolderType.INBOX_TRIAGE, "A_trier", DriveFolderType.INBOX_ROOT),
]

# Project core folders
PROJECT_CORE_FOLDERS = [
    (DriveFolderType.PROJECT_ROOT, None, DriveFolderType.PROJECTS_ROOT),  # Name = project name
    (DriveFolderType.PROJECT_ADMIN, "00_Admin", DriveFolderType.PROJECT_ROOT),
    (DriveFolderType.PROJECT_COMM, "01_Communication", DriveFolderType.PROJECT_ROOT),
    (DriveFolderType.PROJECT_ASSETS, "02_Assets", DriveFolderType.PROJECT_ROOT),
    (DriveFolderType.PROJECT_PROD, "03_Production", DriveFolderType.PROJECT_ROOT),
    (DriveFolderType.PROJECT_DELIVERABLES, "04_Livrables", DriveFolderType.PROJECT_ROOT),
    (DriveFolderType.PROJECT_ARCHIVE, "99_Archive", DriveFolderType.PROJECT_ROOT),
]

# Project Business folders
PROJECT_BUSINESS_FOLDERS = [
    (DriveFolderType.PROJECT_ADMIN_BUSINESS, "Business", DriveFolderType.PROJECT_ADMIN),
    (DriveFolderType.PROJECT_ADMIN_BUSINESS_QUOTES, "Devis", DriveFolderType.PROJECT_ADMIN_BUSINESS),
    (DriveFolderType.PROJECT_ADMIN_BUSINESS_INVOICES, "Factures", DriveFolderType.PROJECT_ADMIN_BUSINESS),
    (DriveFolderType.PROJECT_ADMIN_BUSINESS_VALIDATIONS, "Validations", DriveFolderType.PROJECT_ADMIN_BUSINESS),
]

# Project Analytics folders
PROJECT_ANALYTICS_FOLDERS = [
    (DriveFolderType.PROJECT_ADMIN_REPORTING, "Reporting", DriveFolderType.PROJECT_ADMIN),
]

# Project Intelligence folders
PROJECT_INTELLIGENCE_FOLDERS = [
    (DriveFolderType.PROJECT_ADMIN_SCORING, "Scoring", DriveFolderType.PROJECT_ADMIN),
]

# Project Discovery folders
PROJECT_DISCOVERY_FOLDERS = [
    (DriveFolderType.PROJECT_COMM_WATCH, "Veille", DriveFolderType.PROJECT_COMM),
    (DriveFolderType.PROJECT_ASSETS_REFS, "Refs", DriveFolderType.PROJECT_ASSETS),
]


# ============================================================================
# DRIVE STRUCTURE SERVICE
# ============================================================================

class DriveStructureService:
    """
    Service for managing Google Drive folder structures.
    Ensures idempotent creation and maintenance of workspace hierarchies.
    """

    def __init__(
        self,
        db: Session,
        google_service: GoogleWorkspaceService,
        workspace_id: int,
        google_account_id: str
    ):
        self.db = db
        self.google_service = google_service
        self.workspace_id = workspace_id
        self.google_account_id = google_account_id
        
        # Cache folder IDs during operation
        self._folder_cache: Dict[str, str] = {}

    # ========================================================================
    # PUBLIC METHODS
    # ========================================================================

    async def ensure_workspace_structure(self) -> StructureResult:
        """
        Ensure the complete workspace folder structure exists.
        Called at EVERY Google login to verify and repair structure.
        
        Returns:
            StructureResult with created/restored/reused folders
        """
        result = StructureResult()
        
        try:
            # Get workspace to check enabled packs
            workspace = self.db.query(Workspace).filter(
                Workspace.id == self.workspace_id
            ).first()
            
            if not workspace:
                result.success = False
                result.errors.append(f"Workspace {self.workspace_id} not found")
                return result

            # Determine which folder sets to create
            enabled_packs = workspace.enabled_packs or []
            addons = workspace.addons or []
            settings = workspace.settings or {}
            
            # Check pack/addon flags
            business_enabled = Feature.INVOICES in effective_features(workspace)
            analytics_enabled = Feature.ANALYTICS in effective_features(workspace)
            intelligence_enabled = Feature.ANALYTICS in effective_features(workspace)
            discovery_enabled = Feature.DISCOVERY in effective_features(workspace)
            data_enabled = "data" in enabled_packs
            templates_enabled = settings.get("templates_enabled", True)

            logger.info(
                f"Ensuring Drive structure for workspace {self.workspace_id}: "
                f"business={business_enabled}, analytics={analytics_enabled}, "
                f"discovery={discovery_enabled}, data={data_enabled}"
            )

            # 1. Create core folders (always)
            await self._ensure_folders(CORE_FOLDERS, result)
            
            # 2. Create templates folders if enabled
            if templates_enabled:
                await self._ensure_folders(TEMPLATES_FOLDERS, result)
            
            # 3. Create business folders if addon enabled
            if business_enabled:
                await self._ensure_folders(BUSINESS_FOLDERS, result)
            
            # 4. Create exports folders if analytics or intelligence enabled
            if analytics_enabled or intelligence_enabled:
                await self._ensure_folders(EXPORTS_FOLDERS, result)
            
            # 5. Create discovery folders if discovery pack enabled
            if discovery_enabled:
                await self._ensure_folders(DISCOVERY_FOLDERS, result)
            
            # 6. Create data folders if data pack enabled
            if data_enabled:
                await self._ensure_folders(DATA_FOLDERS, result)
            
            # 7. Create inbox folders (always)
            await self._ensure_folders(INBOX_FOLDERS, result)

            # Update workspace with root folder ID
            if DriveFolderType.ROOT.value in self._folder_cache:
                workspace.drive_root_folder_id = self._folder_cache[DriveFolderType.ROOT.value]
                self.db.commit()

            result.folder_ids = dict(self._folder_cache)
            logger.info(
                f"Drive structure complete: {len(result.created)} created, "
                f"{len(result.restored)} restored, {len(result.reused)} reused"
            )

        except TokenExpiredError as e:
            result.success = False
            result.errors.append("Google authorization expired. Please reconnect.")
            logger.error(f"Token expired during structure creation: {e}")
            raise

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Error ensuring Drive structure: {e}", exc_info=True)

        return result

    async def ensure_project_structure(
        self,
        project_id: int,
        project_name: str
    ) -> StructureResult:
        """
        Ensure project folder structure exists.
        Called when creating a project or opening a project.
        
        Args:
            project_id: The project ID in database
            project_name: The project name (used for folder name)
            
        Returns:
            StructureResult with created/restored/reused folders
        """
        result = StructureResult()
        
        try:
            # First ensure workspace structure exists
            await self.ensure_workspace_structure()
            
            # Get workspace to check packs
            workspace = self.db.query(Workspace).filter(
                Workspace.id == self.workspace_id
            ).first()
            
            if not workspace:
                result.success = False
                result.errors.append(f"Workspace {self.workspace_id} not found")
                return result

            enabled_packs = workspace.enabled_packs or []
            addons = workspace.addons or []
            
            business_enabled = Feature.INVOICES in effective_features(workspace)
            analytics_enabled = Feature.ANALYTICS in effective_features(workspace)
            intelligence_enabled = Feature.ANALYTICS in effective_features(workspace)
            discovery_enabled = Feature.DISCOVERY in effective_features(workspace)

            # Create project core folders
            await self._ensure_project_folders(
                PROJECT_CORE_FOLDERS, 
                project_id, 
                project_name,
                result
            )
            
            # Conditional project folders
            if business_enabled:
                await self._ensure_project_folders(
                    PROJECT_BUSINESS_FOLDERS, 
                    project_id, 
                    project_name,
                    result
                )
            
            if analytics_enabled:
                await self._ensure_project_folders(
                    PROJECT_ANALYTICS_FOLDERS, 
                    project_id, 
                    project_name,
                    result
                )
            
            if intelligence_enabled:
                await self._ensure_project_folders(
                    PROJECT_INTELLIGENCE_FOLDERS, 
                    project_id, 
                    project_name,
                    result
                )
            
            if discovery_enabled:
                await self._ensure_project_folders(
                    PROJECT_DISCOVERY_FOLDERS, 
                    project_id, 
                    project_name,
                    result
                )

            # Update project with root folder ID
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project_root_key = f"PROJECT_{project_id}_ROOT"
                if project_root_key in self._folder_cache:
                    project.drive_folder_id = self._folder_cache[project_root_key]
                    self.db.commit()

            result.folder_ids = {
                k: v for k, v in self._folder_cache.items() 
                if k.startswith(f"PROJECT_{project_id}")
            }

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Error ensuring project structure: {e}", exc_info=True)

        return result

    async def get_folder_id(
        self,
        folder_type: DriveFolderType,
        project_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Get a folder ID from cache or database.
        
        Args:
            folder_type: The type of folder to get
            project_id: Project ID if this is a project folder
            
        Returns:
            Drive folder ID or None if not found
        """
        cache_key = self._get_cache_key(folder_type, project_id)
        
        # Check memory cache
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]
        
        # Check database
        folder_map = self._get_folder_map(folder_type, project_id)
        if folder_map:
            self._folder_cache[cache_key] = folder_map.drive_folder_id
            return folder_map.drive_folder_id
        
        return None

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _get_cache_key(
        self,
        folder_type: DriveFolderType,
        project_id: Optional[int] = None
    ) -> str:
        """Generate cache key for a folder"""
        if project_id:
            return f"PROJECT_{project_id}_{folder_type.value}"
        return folder_type.value

    def _get_folder_map(
        self,
        folder_type: DriveFolderType,
        project_id: Optional[int] = None
    ) -> Optional[DriveFolderMap]:
        """Get folder map from database"""
        query = self.db.query(DriveFolderMap).filter(
            DriveFolderMap.workspace_id == self.workspace_id,
            DriveFolderMap.google_account_id == self.google_account_id,
            DriveFolderMap.folder_type == folder_type.value
        )
        
        if project_id:
            query = query.filter(DriveFolderMap.project_id == project_id)
        else:
            query = query.filter(DriveFolderMap.project_id.is_(None))
        
        return query.first()

    async def _ensure_folders(
        self,
        folder_definitions: List[Tuple],
        result: StructureResult
    ) -> None:
        """
        Ensure a list of folders exist.
        
        Args:
            folder_definitions: List of (folder_type, name, parent_type) tuples
            result: StructureResult to update
        """
        for folder_type, folder_name, parent_type in folder_definitions:
            try:
                await self._ensure_single_folder(
                    folder_type=folder_type,
                    folder_name=folder_name,
                    parent_type=parent_type,
                    project_id=None,
                    result=result
                )
            except Exception as e:
                result.errors.append(f"Failed to create {folder_name}: {str(e)}")
                logger.error(f"Failed to create folder {folder_name}: {e}")

    async def _ensure_project_folders(
        self,
        folder_definitions: List[Tuple],
        project_id: int,
        project_name: str,
        result: StructureResult
    ) -> None:
        """Ensure project folders exist"""
        for folder_type, folder_name, parent_type in folder_definitions:
            try:
                # For PROJECT_ROOT, use project name as folder name
                actual_name = project_name if folder_type == DriveFolderType.PROJECT_ROOT else folder_name
                
                await self._ensure_single_folder(
                    folder_type=folder_type,
                    folder_name=actual_name,
                    parent_type=parent_type,
                    project_id=project_id,
                    result=result
                )
            except Exception as e:
                result.errors.append(f"Failed to create {folder_name}: {str(e)}")
                logger.error(f"Failed to create project folder {folder_name}: {e}")

    async def _ensure_single_folder(
        self,
        folder_type: DriveFolderType,
        folder_name: str,
        parent_type: Optional[DriveFolderType],
        project_id: Optional[int],
        result: StructureResult
    ) -> str:
        """
        Ensure a single folder exists. Creates if missing, verifies if exists.
        
        Returns:
            The Drive folder ID
        """
        cache_key = self._get_cache_key(folder_type, project_id)
        
        # 1. Check if we have it in database
        folder_map = self._get_folder_map(folder_type, project_id)
        
        if folder_map:
            # Verify it still exists in Drive
            exists = await self._verify_folder_exists(folder_map.drive_folder_id)
            
            if exists:
                # Folder exists, update cache and return
                self._folder_cache[cache_key] = folder_map.drive_folder_id
                result.reused.append(folder_name)
                
                # Update verification timestamp
                folder_map.last_verified_at = datetime.utcnow()
                self.db.commit()
                
                return folder_map.drive_folder_id
            else:
                # Folder was deleted, need to recreate
                logger.warning(f"Folder {folder_name} ({folder_map.drive_folder_id}) was deleted, recreating")
                self.db.delete(folder_map)
                self.db.commit()
                folder_map = None

        # 2. Get parent folder ID
        if parent_type is None:
            # Root folder, parent is "root" (My Drive)
            parent_id = "root"
        else:
            parent_cache_key = self._get_cache_key(parent_type, project_id)
            parent_id = self._folder_cache.get(parent_cache_key)
            
            if not parent_id:
                # Parent should have been created before, error
                raise GoogleAPIError(f"Parent folder {parent_type.value} not found")

        # 3. Check if folder exists by name (fallback search)
        existing = await self.google_service.find_folder_by_name(
            folder_name, 
            parent_id if parent_id != "root" else None
        )
        
        if existing:
            folder_id = existing["id"]
            result.restored.append(folder_name)
            logger.info(f"Found existing folder by name: {folder_name} ({folder_id})")
        else:
            # 4. Create the folder
            if parent_id == "root":
                created = await self.google_service.create_folder(folder_name)
            else:
                created = await self.google_service.create_folder(folder_name, parent_id)
            
            folder_id = created["id"]
            result.created.append(folder_name)
            logger.info(f"Created folder: {folder_name} ({folder_id})")

        # 5. Save to database
        folder_path = self._build_folder_path(folder_type, folder_name, parent_type, project_id)
        
        new_map = DriveFolderMap(
            workspace_id=self.workspace_id,
            google_account_id=self.google_account_id,
            folder_type=folder_type.value,
            project_id=project_id,
            drive_folder_id=folder_id,
            drive_parent_id=parent_id if parent_id != "root" else None,
            folder_name=folder_name,
            folder_path=folder_path,
            last_verified_at=datetime.utcnow()
        )
        self.db.add(new_map)
        self.db.commit()

        # 6. Update cache
        self._folder_cache[cache_key] = folder_id
        
        return folder_id

    async def _verify_folder_exists(self, folder_id: str) -> bool:
        """Check if a folder still exists in Drive"""
        try:
            await self.google_service.get_file_metadata(folder_id)
            return True
        except DriveFileNotFoundError:
            return False
        except Exception as e:
            # On other errors, assume it exists to be safe
            logger.warning(f"Error checking folder {folder_id}: {e}")
            return True

    def _build_folder_path(
        self,
        folder_type: DriveFolderType,
        folder_name: str,
        parent_type: Optional[DriveFolderType],
        project_id: Optional[int]
    ) -> str:
        """Build a human-readable folder path"""
        parts = []
        
        # Build path by walking up the parent chain
        current_type = folder_type
        current_name = folder_name
        
        while current_type:
            parts.insert(0, current_name)
            
            if current_type == DriveFolderType.ROOT:
                break
            
            # Find parent definition
            parent_def = self._find_parent_definition(current_type, project_id)
            if parent_def:
                current_type, current_name, _ = parent_def
            else:
                break
        
        return "Radar/" + "/".join(parts[1:]) if len(parts) > 1 else "Radar"

    def _find_parent_definition(
        self,
        folder_type: DriveFolderType,
        project_id: Optional[int]
    ) -> Optional[Tuple]:
        """Find the parent folder definition"""
        all_definitions = (
            CORE_FOLDERS + TEMPLATES_FOLDERS + BUSINESS_FOLDERS +
            EXPORTS_FOLDERS + DISCOVERY_FOLDERS + DATA_FOLDERS + INBOX_FOLDERS
        )
        
        if project_id:
            all_definitions = all_definitions + (
                PROJECT_CORE_FOLDERS + PROJECT_BUSINESS_FOLDERS +
                PROJECT_ANALYTICS_FOLDERS + PROJECT_INTELLIGENCE_FOLDERS +
                PROJECT_DISCOVERY_FOLDERS
            )
        
        for ft, name, parent in all_definitions:
            if ft == folder_type:
                if parent:
                    # Find the parent definition
                    for pft, pname, _ in all_definitions:
                        if pft == parent:
                            return (pft, pname, None)
                break
        
        return None


# ============================================================================
# HELPER FUNCTION
# ============================================================================

async def ensure_drive_structure(
    db: Session,
    user_id: int,
    workspace_id: int,
    google_account_id: str
) -> StructureResult:
    """
    Convenience function to ensure Drive structure exists.
    Called at every Google login.
    
    Args:
        db: Database session
        user_id: User ID for token lookup
        workspace_id: Workspace ID
        google_account_id: Google account email/ID
        
    Returns:
        StructureResult with operation details
    """
    from app.services.google_workspace import GoogleWorkspaceService
    
    google_service = GoogleWorkspaceService(user_id)
    
    service = DriveStructureService(
        db=db,
        google_service=google_service,
        workspace_id=workspace_id,
        google_account_id=google_account_id
    )
    
    return await service.ensure_workspace_structure()


async def ensure_project_drive_structure(
    db: Session,
    user_id: int,
    workspace_id: int,
    google_account_id: str,
    project_id: int,
    project_name: str
) -> StructureResult:
    """
    Convenience function to ensure project Drive structure exists.
    Called when creating or opening a project.
    """
    from app.services.google_workspace import GoogleWorkspaceService
    
    google_service = GoogleWorkspaceService(user_id)
    
    service = DriveStructureService(
        db=db,
        google_service=google_service,
        workspace_id=workspace_id,
        google_account_id=google_account_id
    )
    
    return await service.ensure_project_structure(project_id, project_name)
