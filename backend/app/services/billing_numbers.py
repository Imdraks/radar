"""Allocate final document references atomically; draft invoices have temporary IDs."""

from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from app.db.models.billing import BillingCounter


def next_reference(db, workspace_id, kind, document_date=None):
    year = document_date.year if document_date else datetime.utcnow().year
    counter = BillingCounter.__table__
    statement = insert(counter).values(
        workspace_id=workspace_id, year=year, kind=kind, last_number=1
    )
    statement = statement.on_conflict_do_update(
        index_elements=[counter.c.workspace_id, counter.c.year, counter.c.kind],
        set_={"last_number": counter.c.last_number + 1},
    ).returning(counter.c.last_number)
    number = db.execute(statement).scalar_one()
    return f"{kind}-{year}-{number:04d}"
