"""
Agency Cockpit V2 API - Dashboard, Clients, Deals
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import Request, APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case

from app.db.session import get_db
from app.db.models.agency import (
    Client, Deal, Project, Deliverable, Approval, 
    Asset, AgencyTask, CalendarEvent,
    DealStatus, ProjectStatus, DeliverableStatus, ApprovalStatus, TaskStatus
)
from app.db.models.user import User
from app.db.models.billing import BillingClient
from app.core.encryption import encrypt_iban, decrypt_iban, mask_iban
from app.api.deps import get_current_user, require_workspace_member, get_user_workspace_id, get_current_workspace
from app.schemas.agency import (
    # Client
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
    # Deal
    DealCreate, DealUpdate, DealResponse, DealListResponse,
    # Dashboard
    DashboardV2Response, TodoItem, UrgencyItem, BusinessItem,
    # Pipeline
    PipelineResponse, PipelineColumn,
    DealStatus as DealStatusEnum
)


def require_agency_business(request: Request, workspace=Depends(get_current_workspace)):
    from app.core.subscription import effective_features, Feature
    if request.url.path.rstrip("/").endswith("/dashboard"):
        return
    if Feature.CLIENTS not in effective_features(workspace):
        raise HTTPException(status_code=403, detail="Radar Business requis")

router = APIRouter(dependencies=[Depends(require_agency_business)], prefix="/agency", tags=["agency-cockpit"])


def sync_crm_to_billing(db: Session, crm_client: Client, workspace_id: int, iban: str = None, bic: str = None, bank_name: str = None):
    """Sync CRM client to BillingClient table"""
    # Find existing billing client linked to this CRM client
    billing_client = db.query(BillingClient).filter(
        BillingClient.crm_client_id == crm_client.id
    ).first()
    
    # Extract first contact info
    contact_name = None
    contact_first_name = None
    contact_last_name = None
    contact_email = None
    contact_phone = None
    contact_role = None
    
    if crm_client.contacts and len(crm_client.contacts) > 0:
        first_contact = crm_client.contacts[0] if isinstance(crm_client.contacts, list) else None
        if first_contact:
            contact_name = first_contact.get('name', '')
            contact_email = first_contact.get('email')
            contact_phone = first_contact.get('phone')
            contact_role = first_contact.get('role')
            # Try to split name into first/last
            if contact_name:
                name_parts = contact_name.strip().split(' ', 1)
                contact_first_name = name_parts[0] if len(name_parts) > 0 else None
                contact_last_name = name_parts[1] if len(name_parts) > 1 else None
    
    if billing_client:
        # Update existing
        billing_client.name = crm_client.name
        billing_client.company_name = crm_client.name
        billing_client.email = contact_email
        billing_client.phone = contact_phone
        billing_client.contact_first_name = contact_first_name
        billing_client.contact_last_name = contact_last_name
        billing_client.contact_email = contact_email
        billing_client.contact_phone = contact_phone
        billing_client.contact_role = contact_role
        # Address fields
        billing_client.address_line1 = crm_client.address_line1
        billing_client.address_line2 = crm_client.address_line2
        billing_client.city = crm_client.city
        billing_client.postal_code = crm_client.postal_code
        billing_client.country = crm_client.country or "France"
        # Legal info
        billing_client.siret = crm_client.siret
        billing_client.vat_number = crm_client.vat_number
        billing_client.notes = crm_client.notes
        # Banking info (only update if provided)
        if iban:
            billing_client.iban_encrypted = encrypt_iban(iban)
        if bic is not None:
            billing_client.bic = bic
        if bank_name is not None:
            billing_client.bank_name = bank_name
    else:
        # Create new billing client
        billing_client = BillingClient(
            workspace_id=workspace_id,
            crm_client_id=crm_client.id,
            name=crm_client.name,
            company_name=crm_client.name,
            email=contact_email,
            phone=contact_phone,
            contact_first_name=contact_first_name,
            contact_last_name=contact_last_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            contact_role=contact_role,
            # Address fields
            address_line1=crm_client.address_line1,
            address_line2=crm_client.address_line2,
            city=crm_client.city,
            postal_code=crm_client.postal_code,
            country=crm_client.country or "France",
            # Legal info
            siret=crm_client.siret,
            vat_number=crm_client.vat_number,
            notes=crm_client.notes,
            # Banking info
            iban_encrypted=encrypt_iban(iban) if iban else None,
            bic=bic,
            bank_name=bank_name
        )
        db.add(billing_client)
    
    return billing_client


def delete_billing_client_for_crm(db: Session, crm_client_id: int):
    """Delete BillingClient linked to CRM client"""
    billing_client = db.query(BillingClient).filter(
        BillingClient.crm_client_id == crm_client_id
    ).first()
    if billing_client:
        # Only delete if no quotes/invoices
        if not billing_client.quotes and not billing_client.invoices:
            db.delete(billing_client)
        else:
            # Unlink but keep for historical data
            billing_client.crm_client_id = None


# ============================================================================
# DASHBOARD V2
# ============================================================================

@router.get("/dashboard", response_model=DashboardV2Response)
async def get_dashboard_v2(
    workspace_id: Optional[int] = Query(None, description="Workspace ID (optional, uses user's default)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """
    Dashboard V2 avec 3 blocs :
    - À faire aujourd'hui (relances, validations, tâches)
    - Urgences (deadlines < 72h, projets bloqués)
    - Business (leads chauds, devis envoyés)
    """
    # Get workspace_id - use provided or user's default
    ws_id = get_user_workspace_id(workspace_id, current_user, db)
    
    from app.core.subscription import Feature, effective_features
    has_business = Feature.CLIENTS in effective_features(get_current_workspace(workspace_id, current_user, db))
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    urgency_threshold = now + timedelta(hours=72)
    
    todos = []
    urgencies = []
    business = []
    
    # ========================================================================
    # BLOCK A: À FAIRE AUJOURD'HUI
    # ========================================================================
    
    # 1. Relances (deals avec next_action_date aujourd'hui ou dépassée)
    followups = db.query(Deal).join(Client).filter(
        Client.workspace_id == ws_id,
        Deal.next_action_date <= today_end,
        Deal.status.notin_([DealStatus.WON, DealStatus.LOST])
    ).all()
    
    for deal in followups:
        todos.append(TodoItem(
            id=deal.id,
            type="followup",
            title=f"Relancer: {deal.title}",
            subtitle=f"Dernière action prévue: {deal.next_action_date.strftime('%d/%m') if deal.next_action_date else 'N/A'}",
            due_date=deal.next_action_date,
            priority="high" if deal.next_action_date and deal.next_action_date < now else "medium",
            client_name=deal.client.name if deal.client else None,
            link=f"/pipeline?deal={deal.id}"
        ))
    
    # 2. Validations en attente
    pending_approvals = db.query(Approval).join(Deliverable).join(Project).join(Client).filter(
        Client.workspace_id == ws_id,
        Approval.status == ApprovalStatus.PENDING
    ).all()
    
    for approval in pending_approvals:
        todos.append(TodoItem(
            id=approval.id,
            type="validation",
            title=f"Validation: {approval.deliverable.name}",
            subtitle=f"Projet: {approval.deliverable.project.name}",
            due_date=approval.requested_at,
            priority="high",
            client_name=approval.deliverable.project.client.name if approval.deliverable.project.client else None,
            project_name=approval.deliverable.project.name,
            link=f"/production?deliverable={approval.deliverable_id}"
        ))
    
    # 3. Tâches du jour
    today_tasks = db.query(AgencyTask).join(Project).join(Client).filter(
        Client.workspace_id == ws_id,
        AgencyTask.due_date <= today_end,
        AgencyTask.status != TaskStatus.DONE
    ).all()
    
    for task in today_tasks:
        todos.append(TodoItem(
            id=task.id,
            type="task",
            title=task.title,
            subtitle=f"{'Auto-générée' if task.is_auto_generated else 'Manuelle'}",
            due_date=task.due_date,
            priority=task.priority.value if task.priority else "medium",
            project_name=task.project.name if task.project else None,
            client_name=task.project.client.name if task.project and task.project.client else None,
            link=f"/projects/{task.project_id}" if task.project_id else None
        ))
    
    # ========================================================================
    # BLOCK B: URGENCES
    # ========================================================================
    
    # 1. Deadlines < 72h
    urgent_projects = db.query(Project).join(Client).filter(
        Client.workspace_id == ws_id,
        Project.deadline <= urgency_threshold,
        Project.deadline >= now,
        Project.status == ProjectStatus.ACTIVE
    ).all()
    
    for project in urgent_projects:
        days_remaining = (project.deadline - now).days if project.deadline else None
        urgencies.append(UrgencyItem(
            id=project.id,
            type="deadline",
            title=f"Deadline: {project.name}",
            subtitle=f"Dans {days_remaining}j" if days_remaining is not None else None,
            deadline=project.deadline,
            days_remaining=days_remaining,
            client_name=project.client.name if project.client else None,
            project_name=project.name,
            severity="danger" if days_remaining and days_remaining <= 1 else "warning"
        ))
    
    # 2. Livrables urgents (due_date < 72h et pas approved)
    urgent_deliverables = db.query(Deliverable).join(Project).join(Client).filter(
        Client.workspace_id == ws_id,
        Deliverable.due_date <= urgency_threshold,
        Deliverable.due_date >= now,
        Deliverable.status.notin_([DeliverableStatus.APPROVED, DeliverableStatus.DELIVERED])
    ).all()
    
    for deliverable in urgent_deliverables:
        days_remaining = (deliverable.due_date - now).days if deliverable.due_date else None
        urgencies.append(UrgencyItem(
            id=deliverable.id,
            type="deliverable_deadline",
            title=f"Livrable: {deliverable.name}",
            subtitle=f"Projet: {deliverable.project.name}",
            deadline=deliverable.due_date,
            days_remaining=days_remaining,
            client_name=deliverable.project.client.name if deliverable.project.client else None,
            project_name=deliverable.project.name,
            severity="danger" if days_remaining and days_remaining <= 1 else "warning"
        ))
    
    # 3. Projets bloqués
    blocked_projects = db.query(Project).join(Client).filter(
        Client.workspace_id == ws_id,
        Project.status == ProjectStatus.BLOCKED
    ).all()
    
    for project in blocked_projects:
        urgencies.append(UrgencyItem(
            id=project.id,
            type="blocked_project",
            title=f"Bloqué: {project.name}",
            subtitle="Nécessite une action",
            client_name=project.client.name if project.client else None,
            project_name=project.name,
            severity="danger"
        ))
    
    # 4. Tâches en retard
    overdue_tasks = db.query(AgencyTask).join(Project).join(Client).filter(
        Client.workspace_id == ws_id,
        AgencyTask.due_date < now,
        AgencyTask.status != TaskStatus.DONE
    ).all()
    
    for task in overdue_tasks:
        urgencies.append(UrgencyItem(
            id=task.id,
            type="overdue_task",
            title=f"En retard: {task.title}",
            subtitle=f"Depuis {(now - task.due_date).days}j" if task.due_date else None,
            deadline=task.due_date,
            client_name=task.project.client.name if task.project and task.project.client else None,
            project_name=task.project.name if task.project else None,
            severity="danger"
        ))
    
    # ========================================================================
    # BLOCK C: BUSINESS
    # ========================================================================
    
    # 1. Leads chauds (new ou contacted, récents)
    hot_leads = db.query(Deal).join(Client).filter(
        Client.workspace_id == ws_id,
        Deal.status.in_([DealStatus.NEW, DealStatus.CONTACTED]),
        Deal.created_at >= now - timedelta(days=7)
    ).order_by(Deal.value.desc().nullslast()).limit(10).all()
    
    for deal in hot_leads:
        days_ago = (now - deal.created_at).days if deal.created_at else None
        business.append(BusinessItem(
            id=deal.id,
            type="hot_lead",
            title=deal.title,
            subtitle=f"Reçu il y a {days_ago}j" if days_ago is not None else None,
            value=deal.value,
            client_name=deal.client.name if deal.client else None,
            status=deal.status.value
        ))
    
    # 2. Devis envoyés (en attente de réponse)
    quote_sent = db.query(Deal).join(Client).filter(
        Client.workspace_id == ws_id,
        Deal.status == DealStatus.QUOTE_SENT
    ).all()
    
    for deal in quote_sent:
        days_waiting = (now - deal.last_contact_at).days if deal.last_contact_at else None
        business.append(BusinessItem(
            id=deal.id,
            type="quote_sent",
            title=deal.title,
            subtitle=f"Envoyé il y a {days_waiting}j" if days_waiting is not None else "En attente",
            value=deal.value,
            client_name=deal.client.name if deal.client else None,
            status="quote_sent",
            days_waiting=days_waiting
        ))
    
    # 3. Deals en négociation
    negotiating = db.query(Deal).join(Client).filter(
        Client.workspace_id == ws_id,
        Deal.status == DealStatus.NEGOTIATION
    ).all()
    
    for deal in negotiating:
        business.append(BusinessItem(
            id=deal.id,
            type="negotiation",
            title=deal.title,
            subtitle="En négociation",
            value=deal.value,
            client_name=deal.client.name if deal.client else None,
            status="negotiation"
        ))
    
    # ========================================================================
    # QUICK STATS
    # ========================================================================
    
    active_projects_count = db.query(func.count(Project.id)).join(Client).filter(
        Client.workspace_id == ws_id,
        Project.status == ProjectStatus.ACTIVE
    ).scalar() or 0
    
    pending_validations_count = db.query(func.count(Approval.id)).join(Deliverable).join(Project).join(Client).filter(
        Client.workspace_id == ws_id,
        Approval.status == ApprovalStatus.PENDING
    ).scalar() or 0
    
    hot_leads_count = db.query(func.count(Deal.id)).join(Client).filter(
        Client.workspace_id == ws_id,
        Deal.status.in_([DealStatus.NEW, DealStatus.CONTACTED])
    ).scalar() or 0
    
    # Revenus du mois (deals won ce mois)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = db.query(func.sum(Deal.value)).join(Client).filter(
        Client.workspace_id == ws_id,
        Deal.status == DealStatus.WON,
        Deal.updated_at >= month_start
    ).scalar() or 0
    
    if not has_business:
        todos = [item for item in todos if item.type != "followup"]
        business = []
        hot_leads_count = None
        monthly_revenue = None

    return DashboardV2Response(
        todos=todos[:15],  # Limit
        todos_count=len(todos),
        urgencies=urgencies[:10],
        urgencies_count=len(urgencies),
        business=business[:15],
        business_count=len(business),
        active_projects=active_projects_count,
        pending_validations=pending_validations_count,
        hot_leads=hot_leads_count,
        monthly_revenue=float(monthly_revenue) if monthly_revenue is not None else None
    )


# ============================================================================
# CLIENTS
# ============================================================================

@router.get("/clients", response_model=List[ClientListResponse])
async def list_clients(
    search: Optional[str] = Query(None),
    workspace_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Liste tous les clients du workspace"""
    # Get workspace_id
    ws_id = get_user_workspace_id(workspace_id, current_user, db)
    
    query = db.query(Client).filter(Client.workspace_id == ws_id)
    
    if search:
        query = query.filter(Client.name.ilike(f"%{search}%"))
    
    clients = query.offset(skip).limit(limit).all()
    
    result = []
    for client in clients:
        active_deals = db.query(func.count(Deal.id)).filter(
            Deal.client_id == client.id,
            Deal.status.notin_([DealStatus.WON, DealStatus.LOST])
        ).scalar() or 0
        
        active_projects = db.query(func.count(Project.id)).filter(
            Project.client_id == client.id,
            Project.status == ProjectStatus.ACTIVE
        ).scalar() or 0
        
        result.append(ClientListResponse(
            id=client.id,
            name=client.name,
            contacts=client.contacts or [],
            active_deals_count=active_deals,
            active_projects_count=active_projects
        ))
    
    return result


@router.post("/clients", response_model=ClientResponse)
async def create_client(
    client_in: ClientCreate,
    workspace_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Créer un nouveau client dans le workspace"""
    # Get workspace_id
    ws_id = get_user_workspace_id(workspace_id, current_user, db)
    
    if not ws_id:
        raise HTTPException(status_code=400, detail="Workspace ID required")
    
    client = Client(
        workspace_id=ws_id,
        name=client_in.name,
        contacts=[c.dict() for c in client_in.contacts] if client_in.contacts else [],
        address_line1=client_in.address_line1,
        address_line2=client_in.address_line2,
        city=client_in.city,
        postal_code=client_in.postal_code,
        country=client_in.country or "France",
        siret=client_in.siret,
        vat_number=client_in.vat_number,
        notes=client_in.notes
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    
    # Sync to BillingClient (with banking info)
    billing_client = sync_crm_to_billing(
        db, client, ws_id,
        iban=client_in.iban,
        bic=client_in.bic,
        bank_name=client_in.bank_name
    )
    db.commit()
    
    return ClientResponse(
        id=client.id,
        name=client.name,
        contacts=client_in.contacts,
        address_line1=client.address_line1,
        address_line2=client.address_line2,
        city=client.city,
        postal_code=client.postal_code,
        country=client.country,
        siret=client.siret,
        vat_number=client.vat_number,
        bic=billing_client.bic if billing_client else None,
        bank_name=billing_client.bank_name if billing_client else None,
        iban_masked=mask_iban(decrypt_iban(billing_client.iban_encrypted)) if billing_client and billing_client.iban_encrypted else None,
        notes=client.notes,
        created_at=client.created_at,
        updated_at=client.updated_at
    )


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Détails d'un client"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.workspace_id == ws_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get linked billing client for banking info
    billing_client = db.query(BillingClient).filter(
        BillingClient.crm_client_id == client.id
    ).first()
    
    active_deals = db.query(func.count(Deal.id)).filter(
        Deal.client_id == client.id,
        Deal.status.notin_([DealStatus.WON, DealStatus.LOST])
    ).scalar() or 0
    
    active_projects = db.query(func.count(Project.id)).filter(
        Project.client_id == client.id,
        Project.status == ProjectStatus.ACTIVE
    ).scalar() or 0
    
    total_value = db.query(func.sum(Deal.value)).filter(
        Deal.client_id == client.id,
        Deal.status == DealStatus.WON
    ).scalar() or 0
    
    return ClientResponse(
        id=client.id,
        name=client.name,
        contacts=client.contacts or [],
        address_line1=client.address_line1,
        address_line2=client.address_line2,
        city=client.city,
        postal_code=client.postal_code,
        country=client.country,
        siret=client.siret,
        vat_number=client.vat_number,
        bic=billing_client.bic if billing_client else None,
        bank_name=billing_client.bank_name if billing_client else None,
        iban_masked=mask_iban(decrypt_iban(billing_client.iban_encrypted)) if billing_client and billing_client.iban_encrypted else None,
        notes=client.notes,
        created_at=client.created_at,
        updated_at=client.updated_at,
        active_deals_count=active_deals,
        active_projects_count=active_projects,
        total_value=float(total_value)
    )


@router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Mettre à jour un client"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.workspace_id == ws_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client_in.name is not None:
        client.name = client_in.name
    if client_in.contacts is not None:
        client.contacts = [c.dict() for c in client_in.contacts]
    if client_in.address_line1 is not None:
        client.address_line1 = client_in.address_line1
    if client_in.address_line2 is not None:
        client.address_line2 = client_in.address_line2
    if client_in.city is not None:
        client.city = client_in.city
    if client_in.postal_code is not None:
        client.postal_code = client_in.postal_code
    if client_in.country is not None:
        client.country = client_in.country
    if client_in.siret is not None:
        client.siret = client_in.siret
    if client_in.vat_number is not None:
        client.vat_number = client_in.vat_number
    if client_in.notes is not None:
        client.notes = client_in.notes
    
    # Sync to BillingClient (with banking info if provided)
    sync_crm_to_billing(
        db, client, ws_id,
        iban=client_in.iban,
        bic=client_in.bic,
        bank_name=client_in.bank_name
    )
    
    db.commit()
    db.refresh(client)
    
    return await get_client(client_id, db, current_user)


@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Supprimer un client"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.workspace_id == ws_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Delete or unlink BillingClient first
    delete_billing_client_for_crm(db, client_id)
    
    db.delete(client)
    db.commit()
    return {"status": "deleted"}


# ============================================================================
# DEALS / PIPELINE
# ============================================================================

@router.get("/pipeline", response_model=PipelineResponse)
async def get_pipeline(
    workspace_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Pipeline commercial Kanban"""
    # Get workspace_id
    ws_id = get_user_workspace_id(workspace_id, current_user, db)
    
    columns = []
    total_deals = 0
    total_value = 0
    
    status_labels = {
        DealStatus.NEW: "Nouveaux",
        DealStatus.CONTACTED: "Contactés",
        DealStatus.QUOTE_SENT: "Devis envoyé",
        DealStatus.NEGOTIATION: "Négociation",
        DealStatus.WON: "Gagnés",
        DealStatus.LOST: "Perdus"
    }
    
    now = datetime.utcnow()
    
    for status in DealStatus:
        deals = db.query(Deal).join(Client).filter(
            Client.workspace_id == ws_id,
            Deal.status == status
        ).all()
        
        deal_items = []
        column_value = 0
        
        for deal in deals:
            days_since_contact = None
            if deal.last_contact_at:
                days_since_contact = (now - deal.last_contact_at).days
            
            deal_items.append(DealListResponse(
                id=deal.id,
                title=deal.title,
                status=DealStatusEnum(deal.status.value),
                value=deal.value,
                client_id=deal.client_id,
                client_name=deal.client.name if deal.client else None,
                next_action_date=deal.next_action_date,
                last_contact_at=deal.last_contact_at,
                days_since_contact=days_since_contact,
                owner_name=None,  # TODO: add owner relationship
                tags=deal.tags or []
            ))
            
            if deal.value:
                column_value += deal.value
        
        columns.append(PipelineColumn(
            status=DealStatusEnum(status.value),
            label=status_labels.get(status, status.value),
            deals=deal_items,
            count=len(deal_items),
            total_value=column_value
        ))
        
        total_deals += len(deal_items)
        total_value += column_value
    
    return PipelineResponse(
        columns=columns,
        total_deals=total_deals,
        total_value=total_value
    )


@router.get("/deals", response_model=List[DealListResponse])
async def list_deals(
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    workspace_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Liste des deals du workspace"""
    # Get workspace_id
    ws_id = get_user_workspace_id(workspace_id, current_user, db)
    
    query = db.query(Deal).join(Client).filter(Client.workspace_id == ws_id)
    
    if status:
        # Convert string to enum (case-insensitive)
        try:
            status_enum = DealStatus(status.lower())
            query = query.filter(Deal.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if client_id:
        query = query.filter(Deal.client_id == client_id)
    
    deals = query.offset(skip).limit(limit).all()
    now = datetime.utcnow()
    
    result = []
    for deal in deals:
        days_since_contact = None
        if deal.last_contact_at:
            days_since_contact = (now - deal.last_contact_at).days
        
        result.append(DealListResponse(
            id=deal.id,
            title=deal.title,
            status=DealStatusEnum(deal.status.value),
            value=deal.value,
            client_id=deal.client_id,
            client_name=deal.client.name if deal.client else None,
            next_action_date=deal.next_action_date,
            last_contact_at=deal.last_contact_at,
            days_since_contact=days_since_contact,
            owner_name=deal.owner.email if deal.owner else None,
            tags=deal.tags or []
        ))
    
    return result


@router.post("/deals", response_model=DealResponse)
async def create_deal(
    deal_in: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Créer un nouveau deal"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    # Vérifier que le client existe et appartient au workspace
    client = db.query(Client).filter(
        Client.id == deal_in.client_id,
        Client.workspace_id == ws_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    deal = Deal(
        client_id=deal_in.client_id,
        title=deal_in.title,
        status=deal_in.status.value if deal_in.status else DealStatus.NEW,
        value=deal_in.value,
        next_action_date=deal_in.next_action_date,
        source=deal_in.source,
        tags=deal_in.tags or [],
        notes=deal_in.notes,
        owner_id=current_user.id,
        last_contact_at=datetime.utcnow()
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    
    return DealResponse(
        id=deal.id,
        client_id=deal.client_id,
        title=deal.title,
        status=DealStatusEnum(deal.status.value),
        value=deal.value,
        next_action_date=deal.next_action_date,
        last_contact_at=deal.last_contact_at,
        source=deal.source,
        tags=deal.tags or [],
        notes=deal.notes,
        owner_id=deal.owner_id,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        client_name=client.name
    )


@router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Détails d'un deal"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    deal = db.query(Deal).join(Client).filter(
        Deal.id == deal_id,
        Client.workspace_id == ws_id
    ).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    now = datetime.utcnow()
    days_since_contact = None
    if deal.last_contact_at:
        days_since_contact = (now - deal.last_contact_at).days
    
    return DealResponse(
        id=deal.id,
        client_id=deal.client_id,
        title=deal.title,
        status=DealStatusEnum(deal.status.value),
        value=deal.value,
        next_action_date=deal.next_action_date,
        last_contact_at=deal.last_contact_at,
        source=deal.source,
        tags=deal.tags or [],
        notes=deal.notes,
        owner_id=deal.owner_id,
        legacy_opportunity_id=deal.legacy_opportunity_id,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        client_name=deal.client.name if deal.client else None,
        owner_name=deal.owner.email if deal.owner else None,
        days_since_contact=days_since_contact
    )


@router.put("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: int,
    deal_in: DealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Mettre à jour un deal"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    deal = db.query(Deal).join(Client).filter(
        Deal.id == deal_id,
        Client.workspace_id == ws_id
    ).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    old_status = deal.status
    
    if deal_in.client_id is not None:
        deal.client_id = deal_in.client_id
    if deal_in.title is not None:
        deal.title = deal_in.title
    if deal_in.status is not None:
        deal.status = deal_in.status.value
    if deal_in.value is not None:
        deal.value = deal_in.value
    if deal_in.next_action_date is not None:
        deal.next_action_date = deal_in.next_action_date
    if deal_in.source is not None:
        deal.source = deal_in.source
    if deal_in.tags is not None:
        deal.tags = deal_in.tags
    if deal_in.notes is not None:
        deal.notes = deal_in.notes
    
    # Track contact
    if deal_in.status is not None and deal_in.status.value != old_status.value:
        deal.last_contact_at = datetime.utcnow()
    
    db.commit()
    db.refresh(deal)
    
    return await get_deal(deal_id, db, current_user)


@router.put("/deals/{deal_id}/status")
async def update_deal_status(
    deal_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Quick status update (for kanban drag & drop)"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    deal = db.query(Deal).join(Client).filter(
        Deal.id == deal_id,
        Client.workspace_id == ws_id
    ).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    deal.status = status
    deal.last_contact_at = datetime.utcnow()
    db.commit()
    
    return {"status": "updated", "new_status": status}


@router.delete("/deals/{deal_id}")
async def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Supprimer un deal"""
    # Get user's workspace
    ws_id = getattr(current_user, 'workspace_id', None)
    if not ws_id:
        from app.db.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
        ws_id = member.workspace_id if member else None
    
    deal = db.query(Deal).join(Client).filter(
        Deal.id == deal_id,
        Client.workspace_id == ws_id
    ).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    db.delete(deal)
    db.commit()
    return {"status": "deleted"}
