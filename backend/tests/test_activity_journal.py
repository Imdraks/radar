"""Exercise the real PostgreSQL journal API, including read-only redaction."""

from datetime import datetime
import pytest
from sqlalchemy import event
from app.db.models import ActivityLog

PREFIX = "/api/v1/admin"


def record(db, user=None, **values):
    row = ActivityLog(
        user_id=user.id if user else None,
        user_tracking_id=user.tracking_id if user else "SYSTEM",
        action=values.pop("action", "login"),
        **values,
    )
    db.add(row)
    db.commit()
    return row


@pytest.mark.parametrize(
    "path",
    [
        "/logs",
        "/logs/search",
        "/logs/filters",
        "/logs/stream",
        "/logs/stats",
        "/users/tracking",
    ],
)
def test_explicit_platform_right_required(client, headers, path):
    assert client.get(PREFIX + path).status_code == 401
    assert client.get(PREFIX + path, headers=headers(0)).status_code == 403
    assert client.get(PREFIX + path, headers=headers(2)).status_code == 200


def test_pagination_and_summary_follow_same_filters(
    client, headers, actors, db_session
):
    for i in range(4):
        record(
            db_session, actors[0][0], resource_type="workspace", resource_id=f"B-{i}"
        )
    record(db_session, actors[0][1], action="client.created", resource_type="workspace")
    record(db_session, action="login", resource_type="artist")
    auth = headers(2)
    params = dict(resource_type="workspace", limit=2)
    a = client.get(PREFIX + "/logs/search", params=params, headers=auth).json()
    b = client.get(
        PREFIX + "/logs/search", params={**params, "page": 2}, headers=auth
    ).json()
    assert a["total"] == b["total"] == 5
    assert a["summary"]["authors"] == 2
    assert a["summary"]["logins"] == 4
    assert not {r["id"] for r in a["items"]} & {r["id"] for r in b["items"]}
    assert client.get(PREFIX + "/logs/search?q=%25", headers=auth).json()["total"] == 0
    assert (
        client.get(PREFIX + "/logs/search?unassigned=true", headers=auth).json()[
            "total"
        ]
        == 1
    )
    options = client.get(PREFIX + "/logs/filters", headers=auth).json()
    assert set(options["actions"]) == {"login", "client.created"}
    assert len(options["authors"]) == 2


def test_paris_day_includes_dst_transition(client, headers, db_session):
    for stamp in [
        "2026-10-24T21:59:59",
        "2026-10-24T22:00:00",
        "2026-10-25T22:59:59",
        "2026-10-25T23:00:00",
    ]:
        record(db_session, created_at=datetime.fromisoformat(stamp))
    response = client.get(
        PREFIX + "/logs/search?from_date=2026-10-25&to_date=2026-10-25",
        headers=headers(2),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2


@pytest.mark.parametrize(
    "query",
    [
        "from_date=2026-11-20&to_date=2026-11-19",
        "since_hours=24&from_date=2026-11-19",
        "author_id=1&unassigned=true",
        "to_date=9999-12-31",
        "from_date=0001-01-01",
        "page=0",
        "limit=101",
    ],
)
def test_invalid_filters_rejected(client, headers, query):
    assert (
        client.get(PREFIX + "/logs/search?" + query, headers=headers(2)).status_code
        == 422
    )


def test_redaction_all_read_paths_keeps_original(client, headers, db_session):
    raw = {
        "password": "Never-show-password",
        "otp": "987654",
        "nested": {"access_token": "Never-show-token"},
        "note": "Bearer Never-show-bearer",
        "budget": 1250,
    }
    row = record(db_session, details=raw)
    for path in ["/logs", "/logs/search", "/logs/stream"]:
        result = client.get(PREFIX + path, headers=headers(2))
        assert result.status_code == 200
        assert "Never-show" not in result.text
        assert "987654" not in result.text
        assert "1250" in result.text
    db_session.refresh(row)
    assert row.details == raw
    record(db_session, details=["legacy value"])
    assert client.get(PREFIX + "/logs/search", headers=headers(2)).status_code == 200


def test_read_queries_do_not_grow_per_actor(
    client, headers, actors, db_session, connection
):
    for i in range(30):
        record(db_session, actors[0][i % 4])
    auth = headers(2)
    statements = []

    def track(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(connection, "before_cursor_execute", track)
    try:
        response = client.get(PREFIX + "/logs/search?limit=30", headers=auth)
    finally:
        event.remove(connection, "before_cursor_execute", track)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 30
    assert len(statements) <= 5


def test_platform_flag_allows_viewer_role(client, headers, actors, db_session):
    from app.db.models.user import Role

    actors[0][2].role = Role.VIEWER
    db_session.commit()
    assert client.get(PREFIX + "/logs/search", headers=headers(2)).status_code == 200


def test_projection_handles_legacy_scalar_details_and_signed_urls():
    from app.services.activity_projection import safe_details

    assert safe_details(["legacy"]) == {"value": ["legacy"]}
    projected = safe_details(
        {
            "url": "https://user:password@example.com/path?code=secret&signature=secret",
            "message": "Bearer hide-me",
            "nested": {"session_id": "hide-session"},
        }
    )
    assert "secret" not in str(projected)
    assert "user:password" not in str(projected)
    assert "hide-me" not in str(projected)
    assert "hide-session" not in str(projected)
