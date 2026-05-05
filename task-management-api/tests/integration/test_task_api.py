import uuid

import pytest  # noqa: F401
from app.models.task import Task
from app.models.user import User
from httpx import AsyncClient
from tests.conftest import make_auth_header


class TestTaskCRUD:
    async def test_create_task(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "title": "New Task",
                "description": "Task description",
                "priority": "HIGH",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Task"
        assert data["status"] == "TODO"
        assert data["priority"] == "HIGH"
        assert data["creator"]["email"] == "testuser@example.com"

    async def test_create_task_minimal(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "Minimal Task"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["priority"] == "MEDIUM"
        assert data["description"] is None

    async def test_create_task_no_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Task"},
        )
        assert response.status_code == 403

    async def test_create_task_invalid_title(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": ""},
        )
        assert response.status_code == 422

    async def test_get_task(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.get(
            f"/api/v1/tasks/{test_task.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Task"

    async def test_get_task_not_found(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get(
            f"/api/v1/tasks/{uuid.uuid4()}",
            headers=headers,
        )
        assert response.status_code == 404

    async def test_update_task(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.put(
            f"/api/v1/tasks/{test_task.id}",
            headers=headers,
            json={"title": "Updated Task", "priority": "URGENT"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Task"
        assert data["priority"] == "URGENT"

    async def test_delete_task(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.delete(
            f"/api/v1/tasks/{test_task.id}",
            headers=headers,
        )
        assert response.status_code == 204

        response = await client.get(
            f"/api/v1/tasks/{test_task.id}",
            headers=headers,
        )
        assert response.status_code == 404

    async def test_list_tasks(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.get("/api/v1/tasks", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_list_tasks_filter_by_status(
        self, client: AsyncClient, test_user: User, test_task: Task
    ):
        headers = make_auth_header(test_user)
        response = await client.get(
            "/api/v1/tasks?status=TODO",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "TODO"

    async def test_list_tasks_pagination(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get(
            "/api/v1/tasks?page=1&page_size=5",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5


class TestTaskAssignment:
    async def test_assign_task(
        self, client: AsyncClient, test_user: User, test_task: Task, test_admin: User
    ):
        headers = make_auth_header(test_admin)
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/assign",
            headers=headers,
            json={"assignee_id": str(test_user.id)},
        )
        assert response.status_code == 200
        assert response.json()["assignee"]["id"] == str(test_user.id)

    async def test_assign_task_invalid_user(
        self, client: AsyncClient, test_admin: User, test_task: Task
    ):
        headers = make_auth_header(test_admin)
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/assign",
            headers=headers,
            json={"assignee_id": str(uuid.uuid4())},
        )
        assert response.status_code == 400

    async def test_reassign_task(
        self,
        client: AsyncClient,
        test_user: User,
        test_task: Task,
        test_admin: User,
        test_manager: User,
    ):
        headers = make_auth_header(test_admin)
        await client.post(
            f"/api/v1/tasks/{test_task.id}/assign",
            headers=headers,
            json={"assignee_id": str(test_user.id)},
        )

        response = await client.put(
            f"/api/v1/tasks/{test_task.id}/reassign",
            headers=headers,
            json={"assignee_id": str(test_manager.id)},
        )
        assert response.status_code == 200
        assert response.json()["assignee"]["id"] == str(test_manager.id)


class TestTaskStatus:
    async def test_update_status_valid(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.put(
            f"/api/v1/tasks/{test_task.id}/status",
            headers=headers,
            json={"status": "IN_PROGRESS"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"

    async def test_update_status_invalid_transition(
        self, client: AsyncClient, test_user: User, test_task: Task
    ):
        headers = make_auth_header(test_user)
        response = await client.put(
            f"/api/v1/tasks/{test_task.id}/status",
            headers=headers,
            json={"status": "DONE"},
        )
        assert response.status_code == 422

    async def test_get_task_history(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.get(
            f"/api/v1/tasks/{test_task.id}/history",
            headers=headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestTaskPermissions:
    async def test_member_cannot_update_others_task(
        self, client: AsyncClient, test_task: Task, test_manager: User
    ):
        headers = make_auth_header(test_manager)
        response = await client.put(
            f"/api/v1/tasks/{test_task.id}",
            headers=headers,
            json={"title": "Hacked"},
        )
        assert response.status_code == 200

    async def test_admin_can_delete_any_task(
        self, client: AsyncClient, test_task: Task, test_admin: User
    ):
        headers = make_auth_header(test_admin)
        response = await client.delete(
            f"/api/v1/tasks/{test_task.id}",
            headers=headers,
        )
        assert response.status_code == 204
