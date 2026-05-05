"""End-to-end tests for complete task workflows."""

import pytest  # noqa: F401
from app.models.user import User
from httpx import AsyncClient
from tests.conftest import make_auth_header


class TestTaskLifecycle:
    """Test complete task lifecycle: create -> assign -> progress -> review -> done."""

    async def test_full_task_lifecycle(
        self,
        client: AsyncClient,
        test_user: User,
        test_admin: User,
        test_manager: User,
    ):
        admin_headers = make_auth_header(test_admin)
        user_headers = make_auth_header(test_user)

        # Step 1: Admin creates a task
        create_response = await client.post(
            "/api/v1/tasks",
            headers=admin_headers,
            json={
                "title": "Implement Feature X",
                "description": "Build the new feature X for the product",
                "priority": "HIGH",
            },
        )
        assert create_response.status_code == 201
        task = create_response.json()
        task_id = task["id"]
        assert task["status"] == "TODO"

        # Step 2: Admin assigns to user
        assign_response = await client.post(
            f"/api/v1/tasks/{task_id}/assign",
            headers=admin_headers,
            json={"assignee_id": str(test_user.id)},
        )
        assert assign_response.status_code == 200
        assert assign_response.json()["assignee"]["id"] == str(test_user.id)

        # Step 3: User starts working (TODO -> IN_PROGRESS)
        status_response = await client.put(
            f"/api/v1/tasks/{task_id}/status",
            headers=user_headers,
            json={"status": "IN_PROGRESS"},
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "IN_PROGRESS"

        # Step 4: User adds a comment
        comment_response = await client.post(
            f"/api/v1/tasks/{task_id}/comments",
            headers=user_headers,
            json={"content": "Started working on this. ETA: 2 days."},
        )
        assert comment_response.status_code == 201

        # Step 5: User submits for review (IN_PROGRESS -> IN_REVIEW)
        review_response = await client.put(
            f"/api/v1/tasks/{task_id}/status",
            headers=user_headers,
            json={"status": "IN_REVIEW"},
        )
        assert review_response.status_code == 200
        assert review_response.json()["status"] == "IN_REVIEW"

        # Step 6: Admin marks as done (IN_REVIEW -> DONE)
        done_response = await client.put(
            f"/api/v1/tasks/{task_id}/status",
            headers=admin_headers,
            json={"status": "DONE"},
        )
        assert done_response.status_code == 200
        assert done_response.json()["status"] == "DONE"

        # Step 7: Verify task history shows all transitions
        history_response = await client.get(
            f"/api/v1/tasks/{task_id}/history",
            headers=user_headers,
        )
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) >= 3  # CREATED + STATUS_CHANGE(s) + ASSIGNMENT

        # Step 8: Verify comments
        comments_response = await client.get(
            f"/api/v1/tasks/{task_id}/comments",
            headers=user_headers,
        )
        assert comments_response.status_code == 200
        assert comments_response.json()["total"] >= 1

    async def test_task_cancellation_workflow(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)

        # Create task
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "Task to Cancel"},
        )
        task_id = response.json()["id"]

        # Move to IN_PROGRESS
        await client.put(
            f"/api/v1/tasks/{task_id}/status",
            headers=headers,
            json={"status": "IN_PROGRESS"},
        )

        # Cancel from IN_PROGRESS
        cancel_response = await client.put(
            f"/api/v1/tasks/{task_id}/status",
            headers=headers,
            json={"status": "CANCELLED"},
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "CANCELLED"

        # Cannot transition from CANCELLED
        reopen_response = await client.put(
            f"/api/v1/tasks/{task_id}/status",
            headers=headers,
            json={"status": "TODO"},
        )
        assert reopen_response.status_code == 422

    async def test_register_login_create_task_flow(self, client: AsyncClient):
        # Register
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "e2euser@example.com",
                "password": "E2ePass123",
                "full_name": "E2E User",
            },
        )
        assert reg_response.status_code == 201
        token = reg_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create task with new user
        task_response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "My First Task"},
        )
        assert task_response.status_code == 201

        # Verify user can see their tasks
        list_response = await client.get("/api/v1/tasks", headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()["total"] >= 1
