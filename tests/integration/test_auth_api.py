import pytest  # noqa: F401
from httpx import AsyncClient

from tests.conftest import make_auth_header


class TestRegistration:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "ValidPass1",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["role"] == "MEMBER"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",
                "password": "ValidPass1",
                "full_name": "Another User",
            },
        )
        assert response.status_code == 409

    async def test_register_invalid_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test2@example.com",
                "password": "weak",
                "full_name": "User",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "ValidPass1",
                "full_name": "User",
            },
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["tokens"]

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "WrongPass123",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "SomePass123",
            },
        )
        assert response.status_code == 401


class TestMe:
    async def test_get_me(self, client: AsyncClient, test_user):
        headers = make_auth_header(test_user)
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"

    async def test_get_me_no_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestTokenRefresh:
    async def test_refresh_token(self, client: AsyncClient, test_user):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123",
            },
        )
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 401
