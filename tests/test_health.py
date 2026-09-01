import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == settings.VERSION


@pytest.mark.asyncio
async def test_unhandled_exception_handler():
    @app.get("/test-unhandled-500")
    async def trigger_500():
        raise RuntimeError("Simulated internal server crash")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/test-unhandled-500")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
