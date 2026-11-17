"""Preserve the eager-loadable user relations used by the VPS MCP connector."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.db.models.agency import AgencyTask, Client, Project


@pytest.mark.parametrize('assigned', [True, False])
def test_connector_can_eager_load_project_owner_and_task_assignee(db_session, actors, assigned):
    user, workspace = actors[0][0], actors[1][0]
    customer = Client(name='TEST relation client', workspace_id=workspace.id)
    db_session.add(customer)
    db_session.flush()
    project = Project(name='TEST relation project', client_id=customer.id,
                      workspace_id=workspace.id, owner_id=user.id if assigned else None)
    db_session.add(project)
    db_session.flush()
    task = AgencyTask(title='TEST relation task', project_id=project.id,
                      assignee_id=user.id if assigned else None)
    db_session.add(task)
    db_session.flush()
    project_id, task_id, user_id = project.id, task.id, user.id
    db_session.expunge_all()

    loaded_project = db_session.execute(select(Project).where(Project.id == project_id)
                                      .options(joinedload(Project.owner))).scalar_one()
    loaded_task = db_session.execute(select(AgencyTask).where(AgencyTask.id == task_id)
                                   .options(joinedload(AgencyTask.assignee))).scalar_one()
    # Results must remain usable without a session, just as connector serializers
    # consume eager-loaded users. Unassigned rows must survive the outer joins.
    db_session.expunge_all()
    assert (loaded_project.owner.id if loaded_project.owner else None) == (user_id if assigned else None)
    assert (loaded_task.assignee.id if loaded_task.assignee else None) == (user_id if assigned else None)
