"""Collaborator selection is an entry preference, never a workspace permission."""


def test_only_platform_admin_can_set_collaborator_mode(
    client, headers, actors, db_session
):
    user = actors[0][0]
    user.email = "collaborator@example.com"
    db_session.commit()
    response = client.patch(
        f"/api/v1/users/{user.id}", headers=headers(0), json={"is_collaborator": True}
    )
    assert response.status_code == 403
    db_session.refresh(user)
    assert not user.is_collaborator
    result = client.patch(
        f"/api/v1/users/{user.id}", headers=headers(2), json={"is_collaborator": True}
    )
    assert result.status_code == 200, result.text
    assert result.json()["is_collaborator"] is True
    assert (
        client.get("/api/v1/auth/me", headers=headers(0)).json()["is_collaborator"]
        is True
    )
    assert (
        client.patch(
            f"/api/v1/users/{user.id}",
            headers=headers(2),
            json={"is_collaborator": None},
        ).status_code
        == 422
    )


def test_collaborator_workspaces_are_still_membership_scoped(
    client, headers, actors, db_session
):
    user = actors[0][0]
    user.email = "collaborator@example.com"
    db_session.commit()
    user.is_collaborator = True
    db_session.commit()
    response = client.get("/api/v1/auth/account/workspaces", headers=headers(0))
    assert response.status_code == 200, response.text
    assert {row["id"] for row in response.json()} == {actors[1][0].id}
    assert (
        client.get(
            f"/api/v1/agency/projects?workspace_id={actors[1][1].id}",
            headers=headers(0),
        ).status_code
        == 403
    )
    assert client.get("/api/v1/auth/account/workspaces").status_code == 401
