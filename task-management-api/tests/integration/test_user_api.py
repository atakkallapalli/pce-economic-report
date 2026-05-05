import pytest  # noqa: F401
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import make_auth_header


class TestUserEndpoints:
    async def test_list_users_admin(self, client: AsyncClient, test_admin: User):
        headers = make_auth_header(test_admin)
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_users_manager(self, client: AsyncClient, test_manager: User):
        headers = make_auth_header(test_manager)
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200

    async def test_list_users_member_forbidden(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403

    async def test_get_user_tasks(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.get(
            f"/api/v1/users/{test_user.id}/tasks",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_get_other_user_tasks_member_forbidden(
        self, client: AsyncClient, test_user: User, test_admin: User
    ):
        headers = make_auth_header(test_user)
        response = await client.get(
            f"/api/v1/users/{test_admin.id}/tasks",
            headers=headers,
        )
        assert response.status_code == 403
