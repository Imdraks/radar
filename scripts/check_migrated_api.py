"""API workflow on the database actually built by Alembic, not metadata.create_all.
Called only by the isolated migration harness; API providers are not invoked.
"""

from datetime import datetime
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient


def run(engine):
    if not engine.url.database.startswith("radar_migration_"):
        raise RuntimeError("Migrated API check requires a migration-harness database")
    from app.main import app
    from app.db import get_db
    from app.db.models.user import User, Role
    from app.db.models.workspace import Workspace
    from app.db.models.billing import BillingClient
    from app.core.security import get_password_hash, create_access_token

    with Session(engine) as db:
        user = User(
            email="migrated-api@example.com",
            full_name="TEST migration operator",
            role=Role.ADMIN,
            is_active=True,
            is_whitelisted=True,
            hashed_password=get_password_hash("Disposable-Migration-123!"),
        )
        db.add(user)
        db.flush()
        ws = Workspace(
            name="TEST migration agency",
            owner_user_id=user.id,
            plan="business",
            max_seats=3,
            legal_name="TEST issuer",
            legal_address="1 test street",
            legal_city="Paris",
            legal_postal_code="75001",
            legal_country="France",
            siret="12345678901234",
            tva_franchise=True,
        )
        db.add(ws)
        db.flush()
        customer = BillingClient(
            workspace_id=ws.id,
            name="TEST customer",
            address_line1="2 test street",
            city="Paris",
            postal_code="75002",
            country="France",
        )
        db.add(customer)
        db.flush()
        customer_id = customer.id
        db.commit()

    def database():
        with Session(engine) as db:
            yield db

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    try:
        with patch(
            "app.api.agency_projects.create_project_drive_structure_task",
            lambda **kwargs: None,
        ), TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "migrated-api@example.com",
                    "password": "Disposable-Migration-123!",
                },
            )
            assert login.status_code == 200, login.text
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            project = client.post(
                "/api/v1/agency/projects",
                headers=headers,
                json={"name": "TEST actual migrated project"},
            )
            assert project.status_code == 200, project.text
            assert (
                client.get(
                    f"/api/v1/agency/projects/{project.json()['id']}/detail",
                    headers=headers,
                ).status_code
                == 200
            )
            event = client.post(
                "/api/v1/events",
                headers=headers,
                json={
                    "name": "TEST migrated event",
                    "starts_at": "2027-06-01T12:00:00",
                    "ends_at": "2027-06-01T23:00:00",
                    "forecast_budget": "1000",
                },
            )
            assert event.status_code == 201, event.text
            invoice = client.post(
                "/api/v1/billing/invoices",
                headers=headers,
                json={
                    "title": "TEST migrated invoice",
                    "client_id": customer_id,
                    "items": [
                        {"description": "Service", "quantity": "1", "unit_price": "100"}
                    ],
                },
            )
            assert invoice.status_code == 200, invoice.text
            path = f"/api/v1/billing/invoices/{invoice.json()['id']}"
            assert client.post(path + "/send", headers=headers).status_code == 200
            assert (
                client.patch(
                    path, headers=headers, json={"status": "DRAFT"}
                ).status_code
                == 409
            )
            paid = client.post(
                path + "/payment",
                headers=headers,
                json={"amount_paid": "120", "expected_amount_paid": "0"},
            )
            assert paid.status_code == 200, paid.text
            assert client.get(path + "/pdf", headers=headers).status_code == 200
            print(
                "PASS migrated API: real login, project/detail, event, invoice issue/payment/PDF, forbidden transition",
                flush=True,
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
