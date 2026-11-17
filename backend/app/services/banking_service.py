"""
Banking Service - Business logic for bank connections management
================================================================

Permission model:
- Super admin: enable/disable banking feature per workspace, view metadata only
- Workspace admin: full CRUD on connections, initiate OAuth, manage sync
- Regular user: read-only access to account metadata (no balances by default)

Security:
- All tokens encrypted via Fernet before storage
- Tokens NEVER returned in API responses
- Audit log for all sensitive operations
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.db.models.banking import (
    BankConnection, BankAccount, BankConsent, BankSyncLog,
    BankConnectionStatus, BankAccountType, ConsentType, ConsentStatus,
    SyncStatus, SyncTrigger,
)
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.db.models.user import User, Role
from app.core.encryption import encrypt_sensitive, decrypt_sensitive, mask_iban

logger = logging.getLogger(__name__)


# ============================================================================
# PERMISSION HELPERS
# ============================================================================

def is_workspace_admin(user: User, workspace_id: int, db: Session) -> bool:
    """Check if user is workspace admin or global admin."""
    if user.is_superuser or user.role == Role.ADMIN:
        return True
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.role == WorkspaceRole.ADMIN,
    ).first()
    return member is not None


def is_workspace_member(user: User, workspace_id: int, db: Session) -> bool:
    """Check if user is a member of the workspace."""
    if user.is_superuser or user.role == Role.ADMIN:
        return True
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.workspace_id == workspace_id,
    ).first()
    return member is not None


def is_banking_enabled(workspace_id: int, db: Session) -> bool:
    """Check if banking feature is enabled for the workspace.
    Banking is available when the workspace has the radar_business addon.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return False
    from app.core.subscription import Feature, effective_features
    return Feature.BANKING in effective_features(workspace)


# ============================================================================
# AUDIT HELPERS
# ============================================================================

def _add_audit_entry(connection: BankConnection, event: str, user_id: int, details: str = ""):
    """Add an entry to the connection's audit log."""
    audit_log = connection.audit_log or []
    audit_log.append({
        "event": event,
        "at": datetime.utcnow().isoformat(),
        "by": user_id,
        "details": details,
    })
    connection.audit_log = audit_log


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

def get_connections(
    db: Session,
    workspace_id: int,
    include_accounts: bool = False,
) -> List[BankConnection]:
    """Get all bank connections for a workspace."""
    query = db.query(BankConnection).filter(
        BankConnection.workspace_id == workspace_id
    )
    if include_accounts:
        query = query.options(joinedload(BankConnection.accounts))
    return query.order_by(BankConnection.bank_name).all()


def get_connection_detail(
    db: Session,
    connection_id: int,
    workspace_id: int,
) -> Optional[BankConnection]:
    """Get a single connection with accounts and recent syncs."""
    return db.query(BankConnection).options(
        joinedload(BankConnection.accounts),
        joinedload(BankConnection.consents),
    ).filter(
        BankConnection.id == connection_id,
        BankConnection.workspace_id == workspace_id,
    ).first()


def create_connection(
    db: Session,
    workspace_id: int,
    user_id: int,
    bank_name: str,
    bank_code: Optional[str] = None,
    bank_logo_url: Optional[str] = None,
    bank_country: str = "FR",
    provider: Optional[str] = None,
) -> BankConnection:
    """Create a new bank connection."""
    connection = BankConnection(
        workspace_id=workspace_id,
        bank_name=bank_name,
        bank_code=bank_code,
        bank_logo_url=bank_logo_url,
        bank_country=bank_country,
        provider=provider,
        status=BankConnectionStatus.NOT_CONNECTED,
        connected_by_id=user_id,
        audit_log=[],
    )
    _add_audit_entry(connection, "created", user_id, f"Bank: {bank_name}")
    db.add(connection)
    db.commit()
    db.refresh(connection)
    logger.info(f"Banking connection created: {connection.id} for workspace {workspace_id}")
    return connection


def update_connection_settings(
    db: Session,
    connection: BankConnection,
    user_id: int,
    auto_sync_enabled: Optional[bool] = None,
    sync_frequency_hours: Optional[int] = None,
) -> BankConnection:
    """Update connection settings."""
    changes = []
    if auto_sync_enabled is not None and connection.auto_sync_enabled != auto_sync_enabled:
        connection.auto_sync_enabled = auto_sync_enabled
        changes.append(f"auto_sync={'on' if auto_sync_enabled else 'off'}")
    if sync_frequency_hours is not None and connection.sync_frequency_hours != sync_frequency_hours:
        connection.sync_frequency_hours = sync_frequency_hours
        changes.append(f"frequency={sync_frequency_hours}h")
    
    if changes:
        _add_audit_entry(connection, "settings_updated", user_id, ", ".join(changes))
        db.commit()
        db.refresh(connection)
    return connection


def delete_connection(
    db: Session,
    connection: BankConnection,
    user_id: int,
) -> None:
    """Delete a bank connection and all associated data."""
    connection_id = connection.id
    bank_name = connection.bank_name
    workspace_id = connection.workspace_id
    
    db.delete(connection)
    db.commit()
    logger.info(f"Banking connection deleted: {connection_id} ({bank_name}) "
                f"from workspace {workspace_id} by user {user_id}")


def suspend_connection(
    db: Session,
    connection: BankConnection,
    user_id: int,
) -> BankConnection:
    """Manually suspend a connection."""
    connection.status = BankConnectionStatus.SUSPENDED
    connection.status_message = "Manuellement suspendu"
    _add_audit_entry(connection, "suspended", user_id)
    db.commit()
    db.refresh(connection)
    return connection


def resume_connection(
    db: Session,
    connection: BankConnection,
    user_id: int,
) -> BankConnection:
    """Resume a suspended connection."""
    if connection.status != BankConnectionStatus.SUSPENDED:
        return connection
    connection.status = BankConnectionStatus.CONNECTED
    connection.status_message = None
    _add_audit_entry(connection, "resumed", user_id)
    db.commit()
    db.refresh(connection)
    return connection


# ============================================================================
# OAUTH FLOW
# ============================================================================

def initiate_oauth(
    db: Session,
    connection: BankConnection,
    user_id: int,
    provider: str,
    redirect_url: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Initiate OAuth flow for bank connection.
    Returns (authorization_url, state).
    
    NOTE: In a real implementation, this would call the provider's API
    (Bridge, Plaid, Budget Insight, etc.). For now, we simulate the flow.
    """
    import uuid
    state = str(uuid.uuid4())
    
    connection.status = BankConnectionStatus.CONNECTING
    connection.provider = provider
    _add_audit_entry(connection, "oauth_initiated", user_id, f"Provider: {provider}")
    db.commit()
    
    # TODO: Replace with actual provider API call
    # For now, return a placeholder authorization URL
    authorization_url = f"https://{provider}.example.com/authorize?state={state}&connection_id={connection.id}"
    
    return authorization_url, state


def complete_oauth(
    db: Session,
    connection: BankConnection,
    user_id: int,
    access_token: str,
    refresh_token: Optional[str] = None,
) -> BankConnection:
    """
    Complete OAuth flow after callback.
    Encrypts and stores tokens, updates status.
    """
    # Encrypt tokens before storage
    connection.access_token_encrypted = encrypt_sensitive(access_token)
    if refresh_token:
        connection.refresh_token_encrypted = encrypt_sensitive(refresh_token)
    
    connection.status = BankConnectionStatus.CONNECTED
    connection.status_message = None
    connection.connected_at = datetime.utcnow()
    connection.last_sync_at = datetime.utcnow()
    
    # Set consent expiry (PSD2: 90 days)
    connection.consent_expires_at = datetime.utcnow() + timedelta(days=90)
    
    _add_audit_entry(connection, "oauth_completed", user_id)
    
    # Create AISP consent record
    consent = BankConsent(
        connection_id=connection.id,
        workspace_id=connection.workspace_id,
        consent_type=ConsentType.AISP,
        status=ConsentStatus.ACTIVE,
        granted_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=90),
        scope=["balances", "transactions"],
    )
    db.add(consent)
    db.commit()
    db.refresh(connection)
    return connection


# ============================================================================
# SYNC OPERATIONS
# ============================================================================

def trigger_sync(
    db: Session,
    connection: BankConnection,
    user_id: Optional[int] = None,
    trigger: SyncTrigger = SyncTrigger.MANUAL,
) -> BankSyncLog:
    """
    Trigger a sync for a bank connection.
    Creates a sync log entry and would normally dispatch a Celery task.
    """
    sync_log = BankSyncLog(
        connection_id=connection.id,
        workspace_id=connection.workspace_id,
        status=SyncStatus.RUNNING,
        trigger=trigger,
        started_at=datetime.utcnow(),
        triggered_by_id=user_id,
    )
    db.add(sync_log)
    
    if user_id:
        _add_audit_entry(connection, "sync_triggered", user_id, f"Trigger: {trigger.value}")
    
    db.commit()
    db.refresh(sync_log)
    
    # TODO: Dispatch Celery task for actual sync
    # from app.workers.banking_worker import sync_bank_connection
    # sync_bank_connection.delay(connection.id, sync_log.id)
    
    logger.info(f"Sync triggered for connection {connection.id}, log {sync_log.id}")
    return sync_log


def complete_sync(
    db: Session,
    sync_log: BankSyncLog,
    status: SyncStatus,
    accounts_synced: int = 0,
    transactions_fetched: int = 0,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> BankSyncLog:
    """Complete a sync operation and update connection status."""
    sync_log.status = status
    sync_log.completed_at = datetime.utcnow()
    sync_log.duration_ms = int(
        (sync_log.completed_at - sync_log.started_at).total_seconds() * 1000
    )
    sync_log.accounts_synced = accounts_synced
    sync_log.transactions_fetched = transactions_fetched
    sync_log.error_code = error_code
    sync_log.error_message = error_message
    
    # Update connection status based on sync result
    connection = db.query(BankConnection).filter(
        BankConnection.id == sync_log.connection_id
    ).first()
    if connection:
        if status == SyncStatus.SUCCESS:
            connection.status = BankConnectionStatus.CONNECTED
            connection.status_message = None
            connection.last_sync_at = datetime.utcnow()
            # Schedule next sync
            connection.next_sync_at = (
                datetime.utcnow() + timedelta(hours=connection.sync_frequency_hours)
            )
        elif status == SyncStatus.FAILED:
            connection.status = BankConnectionStatus.SYNC_ERROR
            connection.status_message = error_message or "Échec de la synchronisation"
    
    db.commit()
    db.refresh(sync_log)
    return sync_log


def get_sync_logs(
    db: Session,
    connection_id: int,
    workspace_id: int,
    limit: int = 20,
) -> List[BankSyncLog]:
    """Get sync logs for a connection."""
    return db.query(BankSyncLog).filter(
        BankSyncLog.connection_id == connection_id,
        BankSyncLog.workspace_id == workspace_id,
    ).order_by(BankSyncLog.started_at.desc()).limit(limit).all()


# ============================================================================
# ACCOUNT MANAGEMENT
# ============================================================================

def get_accounts(
    db: Session,
    workspace_id: int,
    connection_id: Optional[int] = None,
    active_only: bool = True,
    visible_only: bool = False,
) -> List[BankAccount]:
    """Get bank accounts for a workspace."""
    query = db.query(BankAccount).filter(
        BankAccount.workspace_id == workspace_id,
    )
    if connection_id:
        query = query.filter(BankAccount.connection_id == connection_id)
    if active_only:
        query = query.filter(BankAccount.is_active == True)
    if visible_only:
        query = query.filter(BankAccount.is_visible == True)
    return query.order_by(BankAccount.display_order, BankAccount.account_name).all()


def update_account_display(
    db: Session,
    account: BankAccount,
    account_name: Optional[str] = None,
    is_visible: Optional[bool] = None,
    display_color: Optional[str] = None,
    display_order: Optional[int] = None,
) -> BankAccount:
    """Update account display settings."""
    if account_name is not None:
        account.account_name = account_name
    if is_visible is not None:
        account.is_visible = is_visible
    if display_color is not None:
        account.display_color = display_color
    if display_order is not None:
        account.display_order = display_order
    db.commit()
    db.refresh(account)
    return account


# ============================================================================
# DASHBOARD / AGGREGATION
# ============================================================================

def get_banking_dashboard(
    db: Session,
    workspace_id: int,
) -> dict:
    """Build banking dashboard data."""
    connections = get_connections(db, workspace_id, include_accounts=True)
    
    active_connections = [c for c in connections if c.status == BankConnectionStatus.CONNECTED]
    
    # Aggregate balances by currency
    total_balances = {}
    total_accounts = 0
    for conn in connections:
        for acc in (conn.accounts or []):
            if acc.is_active and acc.balance is not None:
                currency = acc.currency or "EUR"
                total_balances[currency] = total_balances.get(currency, Decimal("0")) + acc.balance
                total_accounts += 1
    
    # Status summary
    status_summary = {}
    for conn in connections:
        status_summary[conn.status.value] = status_summary.get(conn.status.value, 0) + 1
    
    # Expiring consents (within 14 days)
    threshold = datetime.utcnow() + timedelta(days=14)
    expiring_consents = db.query(func.count(BankConsent.id)).filter(
        BankConsent.workspace_id == workspace_id,
        BankConsent.status == ConsentStatus.ACTIVE,
        BankConsent.expires_at <= threshold,
    ).scalar() or 0
    
    # Last sync
    last_sync = None
    for conn in connections:
        if conn.last_sync_at:
            if last_sync is None or conn.last_sync_at > last_sync:
                last_sync = conn.last_sync_at
    
    return {
        "banking_enabled": is_banking_enabled(workspace_id, db),
        "total_connections": len(connections),
        "active_connections": len(active_connections),
        "total_accounts": total_accounts,
        "connections": connections,
        "total_balances": {k: float(v) for k, v in total_balances.items()},
        "status_summary": status_summary,
        "expiring_consents": expiring_consents,
        "last_sync_at": last_sync,
    }


# ============================================================================
# ADMIN OPERATIONS (Super admin only)
# ============================================================================

def toggle_banking_feature(
    db: Session,
    workspace_id: int,
    enabled: bool,
) -> bool:
    """Enable or disable banking for a workspace (super admin only)."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return False
    
    settings = workspace.settings or {}
    settings["banking_enabled"] = enabled
    workspace.settings = settings
    
    # Force SQLAlchemy to detect the JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(workspace, "settings")
    
    db.commit()
    logger.info(f"Banking {'enabled' if enabled else 'disabled'} for workspace {workspace_id}")
    return True


def get_workspace_banking_status(
    db: Session,
    workspace_id: int,
) -> dict:
    """Get banking status for a workspace (admin overview, no credentials)."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return {}
    
    connections_count = db.query(func.count(BankConnection.id)).filter(
        BankConnection.workspace_id == workspace_id,
    ).scalar() or 0
    
    active_count = db.query(func.count(BankConnection.id)).filter(
        BankConnection.workspace_id == workspace_id,
        BankConnection.status == BankConnectionStatus.CONNECTED,
    ).scalar() or 0
    
    last_sync = db.query(func.max(BankConnection.last_sync_at)).filter(
        BankConnection.workspace_id == workspace_id,
    ).scalar()
    
    return {
        "workspace_id": workspace_id,
        "workspace_name": workspace.name,
        "banking_enabled": is_banking_enabled(workspace_id, db),
        "connections_count": connections_count,
        "active_connections": active_count,
        "last_sync_at": last_sync,
    }
