"""Reuse the existing required Client relation for internal production projects."""
from app.db.models.agency import Client
from app.db.models.workspace import Workspace


def internal_client(db, workspace_id):
    # Lock workspace to avoid duplicate contexts on simultaneous project creation.
    db.query(Workspace).filter_by(id=workspace_id).with_for_update().one()
    client = db.query(Client).filter_by(workspace_id=workspace_id, name="Production interne").first()
    if not client:
        client = Client(workspace_id=workspace_id, name="Production interne")
        db.add(client)
        db.flush()
    return client
