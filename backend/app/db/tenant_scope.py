"""Scope request Sessions by organization, including relations with legacy nullable IDs.
Workers and dedicated platform administration retain explicit scoping.
"""
from sqlalchemy import event, or_
from sqlalchemy.orm import Session, with_loader_criteria
from app.db.base import Base


@event.listens_for(Session, "do_orm_execute")
def apply_workspace_scope(state):
    workspace_id = state.session.info.get("workspace_id")
    if workspace_id is None or not (state.is_select or state.is_update or state.is_delete):
        return
    from app.db.models.agency import Client, Project, Asset, AgencyTask, Deliverable, Approval, ProjectActivityLog, Deal
    from app.db.models.discovery import DiscoveryArtist, DiscoverySnapshot, DiscoveryComputedMetrics
    from app.db.models.billing import Quote, QuoteItem, Invoice, InvoiceItem
    related = {
        # Client is the authoritative owner of legacy project rows whose workspace_id may be NULL.
        Project: Project.client.has(Client.workspace_id == workspace_id),
        Asset: Asset.project.has(Project.client.has(Client.workspace_id == workspace_id)),
        Deliverable: Deliverable.project.has(Project.client.has(Client.workspace_id == workspace_id)),
        Approval: Approval.deliverable.has(Deliverable.project.has(Project.client.has(Client.workspace_id == workspace_id))),
        AgencyTask: or_(AgencyTask.project.has(Project.client.has(Client.workspace_id == workspace_id)), AgencyTask.deal.has(Deal.client.has(Client.workspace_id == workspace_id))),
        ProjectActivityLog: ProjectActivityLog.project.has(Project.client.has(Client.workspace_id == workspace_id)),
        DiscoverySnapshot: DiscoverySnapshot.artist.has(DiscoveryArtist.workspace_id == workspace_id),
        DiscoveryComputedMetrics: DiscoveryComputedMetrics.artist.has(DiscoveryArtist.workspace_id == workspace_id),
        QuoteItem: QuoteItem.quote.has(Quote.workspace_id == workspace_id),
        InvoiceItem: InvoiceItem.invoice.has(Invoice.workspace_id == workspace_id),
    }
    for mapper in Base.registry.mappers:
        model = mapper.class_
        if model in related:
            condition = related[model]
        elif hasattr(model, "workspace_id"):
            condition = model.workspace_id == workspace_id
        else:
            continue
        state.statement = state.statement.options(with_loader_criteria(model, condition, include_aliases=True))
