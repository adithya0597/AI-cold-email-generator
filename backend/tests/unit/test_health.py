"""
Tests for the /api/v1/health endpoint.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    """Health endpoint should always return 200 (even if dependencies are down)."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "environment" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_health_contains_service_checks(client: AsyncClient):
    """Health response should report on Redis and database connectivity."""
    response = await client.get("/api/v1/health")
    data = response.json()

    services = data["services"]
    assert "redis" in services
    assert "database" in services
    # In test env without real services, both may be False (degraded)
    assert isinstance(services["redis"], bool)
    assert isinstance(services["database"], bool)
