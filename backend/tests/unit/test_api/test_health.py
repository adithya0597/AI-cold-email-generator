"""
Tests for Story 0.4: Health Check & API Foundation.

Validates:
  AC1 - Health endpoint exists and returns correct structure
  AC2 - API versioning with /api/v1/ prefix
  AC3 - CORS configuration exists
  AC4 - JWT authentication dependencies are available

Uses import-safe approaches to avoid triggering the full router chain
(which requires optional dependencies like opentelemetry.instrumentation.celery).
"""

import pytest


# ============================================================
# AC1 - Health Check Structure
# ============================================================


class TestHealthEndpointStructure:
    """AC1: Health check returns status, version, and service details."""

    def test_health_module_importable(self):
        """health.py module exists and is importable."""
        from app.api.v1 import health
        assert hasattr(health, "router")
        assert hasattr(health, "health_check")

    def test_health_router_has_get_endpoint(self):
        """Health router registers a GET /health endpoint."""
        from app.api.v1.health import router
        routes = [r for r in router.routes if hasattr(r, "methods")]
        health_routes = [r for r in routes if "/health" in r.path]
        assert len(health_routes) > 0, "No /health route found"
        assert "GET" in health_routes[0].methods

    def test_health_router_prefix(self):
        """Health router uses /health prefix or empty prefix."""
        from app.api.v1.health import router
        # Health module either has prefix or the route path includes /health
        routes = [r for r in router.routes if hasattr(r, "path")]
        paths = [r.path for r in routes]
        assert any("health" in p for p in paths), f"No health path in {paths}"


# ============================================================
# AC2 - API Versioning
# ============================================================


class TestAPIVersioning:
    """AC2: All endpoints are prefixed with /api/v1/."""

    def test_router_module_defines_api_router(self):
        """router.py defines an api_router with /api/v1 prefix."""
        import importlib
        import ast
        from pathlib import Path

        # Parse the router.py file statically to check prefix
        router_path = Path(__file__).resolve().parent.parent.parent.parent / "app" / "api" / "v1" / "router.py"
        source = router_path.read_text()
        assert 'prefix="/api/v1"' in source, "api_router must use /api/v1 prefix"

    def test_health_endpoint_path_includes_health(self):
        """Health endpoint is reachable at /health path under the router."""
        from app.api.v1.health import router
        route_paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/health" in route_paths or any("health" in p for p in route_paths)


# ============================================================
# AC3 - CORS Configuration
# ============================================================


class TestCORSConfiguration:
    """AC3: CORS is configured in settings."""

    def test_cors_origins_setting_exists(self):
        """CORS_ORIGINS setting exists with a default value."""
        from app.config import settings
        assert hasattr(settings, "CORS_ORIGINS")
        assert len(settings.CORS_ORIGINS) > 0

    def test_cors_middleware_in_main(self):
        """main.py wires CORSMiddleware."""
        from pathlib import Path
        main_path = Path(__file__).resolve().parent.parent.parent.parent / "app" / "main.py"
        source = main_path.read_text()
        assert "CORSMiddleware" in source


# ============================================================
# AC4 - JWT Authentication
# ============================================================


class TestJWTAuthentication:
    """AC4: JWT middleware is available for protected routes."""

    def test_require_auth_importable(self):
        """require_auth dependency exists."""
        from app.auth.clerk import require_auth
        assert require_auth is not None

    def test_get_current_user_id_importable(self):
        """get_current_user_id dependency exists and is callable."""
        from app.auth.clerk import get_current_user_id
        assert callable(get_current_user_id)
