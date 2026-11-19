"""Only a suspended workspace can be removed; all customer records stay retained."""

from sqlalchemy import select
import pytest
from app.db.models.workspace import Workspace, WorkspaceMember
from app.db.models.user import User
from app.db.models.subscription_request import SubscriptionRequest
from app.db.models.billing import BillingCounter
from app.db.models.activity_log import ActivityLog


def payload(workspace):
    return {
        "confirm_name": workspace.name,
        "reason": "TEST contract terminated",
        "acknowledged": True,
    }


@pytest.mark.parametrize("prefix", ["/api/v1/admin/clients", "/api/v1/workspaces"])
def test_active_workspace_cannot_be_deleted_even_by_superadmin(
    client, db_session, actors, headers, prefix
):
    ws = actors[1][0]
    response = client.request(
        "DELETE", f"{prefix}/{ws.id}", headers=headers(2), json=payload(ws)
    )
    assert response.status_code == 409, response.text
    assert (
        db_session.execute(
            select(Workspace.__table__.c.deleted_at).where(
                Workspace.__table__.c.id == ws.id
            )
        ).scalar_one()
        is None
    )


def test_suspended_deletion_is_confirmed_hidden_and_preserves_accounts_business_and_other_tenants(
    client, db_session, actors, headers
):
    ws = actors[1][0]
    ws.is_suspended = True
    bill = BillingCounter(workspace_id=ws.id, year=2026, kind="invoice", last_number=7)
    order = SubscriptionRequest(
        workspace_id=ws.id,
        requested_by=actors[0][0].id,
        kind="plan",
        requested_value="business",
        status="pending",
    )
    db_session.add_all([bill, order])
    db_session.commit()
    wid = ws.id
    users = db_session.query(User).count()
    members = db_session.query(WorkspaceMember).count()
    admin = headers(2)
    wrong = {**payload(ws), "confirm_name": "Wrong enterprise"}
    assert (
        client.request(
            "DELETE", f"/api/v1/admin/clients/{wid}", headers=admin, json=wrong
        ).status_code
        == 409
    )
    assert (
        client.request(
            "DELETE",
            f"/api/v1/admin/clients/{wid}",
            headers=admin,
            json={**payload(ws), "acknowledged": False},
        ).status_code
        == 422
    )
    result = client.request(
        "DELETE", f"/api/v1/admin/clients/{wid}", headers=admin, json=payload(ws)
    )
    assert result.status_code == 204, result.text
    retained = db_session.execute(
        select(
            Workspace.__table__.c.deleted_at, Workspace.__table__.c.deleted_by
        ).where(Workspace.__table__.c.id == wid)
    ).one()
    assert retained.deleted_at and retained.deleted_by == actors[0][2].id
    assert (
        db_session.query(User).count() == users
        and db_session.query(WorkspaceMember).count() == members
    )
    assert (
        db_session.query(BillingCounter).filter_by(workspace_id=wid).one().last_number
        == 7
    )
    assert (
        db_session.query(SubscriptionRequest).filter_by(id=order.id).one().status
        == "pending"
    )
    assert (
        db_session.query(ActivityLog)
        .filter_by(action="client.deleted", resource_id=str(wid))
        .count()
        == 1
    )
    assert db_session.query(Workspace).filter_by(id=wid).first() is None
    assert db_session.query(Workspace).filter_by(id=actors[1][1].id).first() is not None
    listing = client.get("/api/v1/admin/clients", headers=admin).json()
    assert wid not in {row["id"] for row in listing["items"]}
    assert (
        client.get("/api/v1/admin/clients/" + str(wid), headers=admin).status_code
        == 404
    )
    assert (
        client.get("/api/v1/workspaces/" + str(wid), headers=admin).status_code == 404
    )
    assert (
        client.get("/api/v1/workspaces/" + str(wid), headers=headers(0)).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/agency/projects?workspace_id={wid}", headers=headers(0)
        ).status_code
        == 403
    )
    assert all(
        row["id"] != wid
        for row in client.get(
            "/api/v1/auth/account/workspaces", headers=headers(0)
        ).json()
    )
    assert (
        client.post(
            f"/api/v1/admin/clients/{wid}/suspension",
            headers=admin,
            json={"suspended": False, "reason": "TEST cannot reactivate deleted"},
        ).status_code
        == 404
    )
    assert (
        client.request(
            "DELETE", f"/api/v1/admin/clients/{wid}", headers=admin, json=payload(ws)
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/subscription/admin/requests/{order.id}/decision",
            headers=admin,
            json={
                "approve": False,
                "authorization_reference": "TEST cannot process deleted workspace",
            },
        ).status_code
        == 404
    )


@pytest.mark.parametrize("prefix", ["/api/v1/admin/clients", "/api/v1/workspaces"])
def test_owner_or_another_agency_cannot_delete_a_workspace(
    client, db_session, actors, headers, prefix
):
    ws = actors[1][0]
    ws.is_suspended = True
    db_session.commit()
    for index in [0, 1]:
        assert (
            client.request(
                "DELETE", f"{prefix}/{ws.id}", headers=headers(index), json=payload(ws)
            ).status_code
            == 403
        )
    assert (
        client.request("DELETE", f"{prefix}/{ws.id}", json=payload(ws)).status_code
        == 401
    )


def test_legacy_delete_has_the_same_retention_and_suspension_rules(
    client, db_session, actors, headers
):
    ws = actors[1][0]
    ws.is_suspended = True
    db_session.commit()
    response = client.request(
        "DELETE", f"/api/v1/workspaces/{ws.id}", headers=headers(2), json=payload(ws)
    )
    assert response.status_code == 204, response.text
    assert db_session.execute(
        select(Workspace.__table__.c.deleted_at).where(
            Workspace.__table__.c.id == ws.id
        )
    ).scalar_one()
