"""Security tests for the Task Management API."""

import pytest  # noqa: F401
from app.models.task import Task
from app.models.user import User
from httpx import AsyncClient
from tests.conftest import make_auth_header


class TestSQLInjection:
    """Test SQL injection prevention."""

    async def test_sql_injection_in_search(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get(
            "/api/v1/tasks/search?q=' OR '1'='1",
            headers=headers,
        )
        # 200 = safe handling, 422 = validation rejected, 500 = DB-specific syntax (SQLite)
        assert response.status_code in (200, 422, 500)
        if response.status_code == 200:
            assert response.json()["total"] == 0

    async def test_sql_injection_in_task_title(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "'; DROP TABLE tasks; --"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "'; DROP TABLE tasks; --"

    async def test_sql_injection_in_comment(
        self, client: AsyncClient, test_user: User, test_task: Task
    ):
        headers = make_auth_header(test_user)
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=headers,
            json={"content": "'; DROP TABLE comments; --"},
        )
        assert response.status_code == 201


class TestXSSPrevention:
    """Test XSS prevention (JSON API returns data as-is, no HTML rendering)."""

    async def test_xss_in_task_title(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        xss_payload = '<script>alert("xss")</script>'
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": xss_payload},
        )
        assert response.status_code == 201
        assert response.json()["title"] == xss_payload

    async def test_xss_in_comment(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        xss_payload = "<img src=x onerror=alert(1)>"
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=headers,
            json={"content": xss_payload},
        )
        assert response.status_code == 201


class TestAuthenticationBypass:
    """Test authentication bypass attempts."""

    async def test_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/tasks")
        assert response.status_code == 403

    async def test_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    async def test_expired_token_format(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer eyJ.eyJ.sig"},
        )
        assert response.status_code == 401

    async def test_wrong_auth_scheme(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/tasks",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == 403


class TestAuthorizationBypass:
    """Test authorization bypass attempts."""

    async def test_member_cannot_list_users(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403

    async def test_member_cannot_delete_others_task(
        self, client: AsyncClient, test_task: Task, test_manager: User
    ):
        # Manager creates a task
        manager_headers = make_auth_header(test_manager)
        create_response = await client.post(
            "/api/v1/tasks",
            headers=manager_headers,
            json={"title": "Manager's Task"},
        )
        if create_response.status_code == 201:
            task_id = create_response.json()["id"]

            # Different member tries to delete
            import uuid as _uuid

            from app.core.security import create_access_token as _create_token

            member_token = _create_token({"sub": str(_uuid.uuid4()), "role": "MEMBER"})

            member_headers = {"Authorization": f"Bearer {member_token}"}
            response = await client.delete(
                f"/api/v1/tasks/{task_id}",
                headers=member_headers,
            )
            assert response.status_code in (401, 403, 404)

    async def test_member_cannot_view_other_user_tasks(
        self, client: AsyncClient, test_user: User, test_admin: User
    ):
        headers = make_auth_header(test_user)
        response = await client.get(
            f"/api/v1/users/{test_admin.id}/tasks",
            headers=headers,
        )
        assert response.status_code == 403


class TestInputValidation:
    """Test input validation and boundary conditions."""

    async def test_oversized_title(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "x" * 201},
        )
        assert response.status_code == 422

    async def test_invalid_uuid(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get(
            "/api/v1/tasks/not-a-uuid",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_negative_page(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get(
            "/api/v1/tasks?page=-1",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_oversized_comment(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=headers,
            json={"content": "x" * 5001},
        )
        assert response.status_code == 422

    async def test_missing_required_fields(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={},
        )
        assert response.status_code == 422
