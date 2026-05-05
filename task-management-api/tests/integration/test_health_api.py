import pytest  # noqa: F401
from httpx import AsyncClient


class TestHealthEndpoints:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    async def test_readiness_check(self, client: AsyncClient):
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
