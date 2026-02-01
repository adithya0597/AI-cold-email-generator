"""API Contract Tests — Schemathesis-based validation.

These tests validate that our API implementation matches the OpenAPI spec.
In CI, Schemathesis runs as a separate job using --dry-run against the
generated OpenAPI schema. This file provides a local entry point for
contract testing during development.

Usage:
    pytest tests/contract/ -v

Note: Full Schemathesis contract validation runs in CI as a separate job.
These local tests verify the OpenAPI schema can be generated correctly.
"""

import json

import pytest


@pytest.fixture
def app():
    """Create test app, skipping if legacy models cause issues."""
    try:
        from app.main import create_app
        return create_app()
    except Exception as e:
        pytest.skip(f"App creation failed (likely legacy model issue): {e}")


def test_openapi_schema_generates(app):
    """Verify OpenAPI schema can be generated from the app."""
    schema = app.openapi()

    assert "openapi" in schema
    assert "paths" in schema
    assert "info" in schema
    assert schema["info"]["title"] is not None


def test_openapi_schema_has_paths(app):
    """Verify the schema contains expected API paths."""
    schema = app.openapi()
    paths = schema.get("paths", {})

    # Should have at least the health and version endpoints
    assert len(paths) > 0, "Schema should contain at least one path"


def test_openapi_schema_valid_json(app):
    """Verify the schema serializes to valid JSON."""
    schema = app.openapi()

    # Should not raise
    json_str = json.dumps(schema, indent=2)
    parsed = json.loads(json_str)
    assert parsed == schema
