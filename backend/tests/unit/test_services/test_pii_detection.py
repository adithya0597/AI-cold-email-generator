"""Tests for PII Detection Service and enterprise PII endpoints.

Covers:
- Regex-based pattern detection (default + custom patterns)
- Whitelist exclusion
- Invalid regex validation
- Anonymized alert creation (hashed user_id, no text content)
- PII hook check_pii() return values
- RBAC enforcement (403 for non-admin)
- Pattern CRUD via API
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.enterprise.pii_detection import (
    DEFAULT_PATTERNS,
    PIICheckResult,
    PIIDetection,
    PIIDetectionService,
)


# ---------------------------------------------------------------------------
# Helpers: lightweight fakes for SQLAlchemy
# ---------------------------------------------------------------------------


class FakeScalarResult:
    """Mimics a SQLAlchemy result that returns a scalar value."""

    def __init__(self, value: Any = None):
        self._value = value

    def scalar(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        if isinstance(self._value, list):
            return self._value
        return [self._value] if self._value is not None else []

    def first(self):
        return self._value


class FakeSession:
    """Minimal async session fake."""

    def __init__(self, execute_results: list | None = None):
        self._execute_results = execute_results or []
        self._call_idx = 0
        self._added: list = []

    async def execute(self, stmt, *args, **kwargs):
        if self._call_idx < len(self._execute_results):
            result = self._execute_results[self._call_idx]
            self._call_idx += 1
            return result
        return FakeScalarResult(None)

    def add(self, obj):
        self._added.append(obj)

    async def commit(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Test: Default pattern detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_detects_internal_email():
    """Default internal email pattern should match @company.internal addresses."""
    service = PIIDetectionService()
    settings = {}  # No custom patterns, no whitelist

    # Two calls to execute: _load_patterns, _apply_whitelist
    session = FakeSession([
        FakeScalarResult(settings),  # _load_patterns
        FakeScalarResult(settings),  # _apply_whitelist
    ])

    text = "Contact me at john.doe@acme.internal for details."
    detections = await service.scan_text(text, org_id="org-1", session=session)

    assert len(detections) >= 1
    email_detections = [d for d in detections if d.category == "internal_email"]
    assert len(email_detections) == 1
    assert email_detections[0].matched_term == "john.doe@acme.internal"


@pytest.mark.asyncio
async def test_scan_detects_internal_url():
    """Default internal URL pattern should match .internal URLs."""
    service = PIIDetectionService()
    settings = {}

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "See the docs at https://wiki.corp.internal/page for more info."
    detections = await service.scan_text(text, org_id="org-1", session=session)

    url_detections = [d for d in detections if d.category == "internal_url"]
    assert len(url_detections) == 1
    assert "wiki.corp.internal" in url_detections[0].matched_term


@pytest.mark.asyncio
async def test_scan_detects_code_name():
    """Default code name pattern should match 'Project Phoenix' style names."""
    service = PIIDetectionService()
    settings = {}

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "I led Project Phoenix which delivered ahead of schedule."
    detections = await service.scan_text(text, org_id="org-1", session=session)

    code_name_detections = [d for d in detections if d.category == "code_name"]
    assert len(code_name_detections) >= 1
    assert any("Project Phoenix" in d.matched_term for d in code_name_detections)


# ---------------------------------------------------------------------------
# Test: Custom pattern detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_detects_custom_pattern():
    """Org-configured custom patterns should be merged with defaults."""
    service = PIIDetectionService()
    settings = {
        "pii_patterns": [
            {
                "pattern": r"\bUltraSecretX\b",
                "category": "proprietary_term",
                "description": "Internal product name",
                "enabled": True,
            }
        ],
        "pii_whitelist": [],
    }

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "I worked on UltraSecretX platform integration."
    detections = await service.scan_text(text, org_id="org-1", session=session)

    custom = [d for d in detections if d.category == "proprietary_term"]
    assert len(custom) == 1
    assert custom[0].matched_term == "UltraSecretX"


@pytest.mark.asyncio
async def test_disabled_pattern_skipped():
    """Patterns with enabled=False should not produce detections."""
    service = PIIDetectionService()
    settings = {
        "pii_patterns": [
            {
                "pattern": r"\bSecretProject\b",
                "category": "code_name",
                "description": "Disabled pattern",
                "enabled": False,
            }
        ],
    }

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "I worked on SecretProject last year."
    detections = await service.scan_text(text, org_id="org-1", session=session)

    # Should not have any detections for the disabled custom pattern category
    custom = [d for d in detections if d.matched_term == "SecretProject"]
    assert len(custom) == 0


# ---------------------------------------------------------------------------
# Test: Whitelist exclusion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_whitelist_excludes_term():
    """Whitelisted terms should be excluded from detection results."""
    service = PIIDetectionService()
    settings = {
        "pii_patterns": [],
        "pii_whitelist": ["Project Phoenix"],
    }

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "I led Project Phoenix which delivered ahead of schedule."
    detections = await service.scan_text(text, org_id="org-1", session=session)

    # The default code_name pattern would match "Project Phoenix" but whitelist filters it
    phoenix_hits = [d for d in detections if "Project Phoenix" in d.matched_term]
    assert len(phoenix_hits) == 0


@pytest.mark.asyncio
async def test_whitelist_case_insensitive():
    """Whitelist matching should be case-insensitive."""
    service = PIIDetectionService()
    settings = {
        "pii_patterns": [],
        "pii_whitelist": ["project phoenix"],  # lowercase
    }

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "I led Project Phoenix which delivered ahead of schedule."
    detections = await service.scan_text(text, org_id="org-1", session=session)

    phoenix_hits = [d for d in detections if "Project Phoenix" in d.matched_term]
    assert len(phoenix_hits) == 0


# ---------------------------------------------------------------------------
# Test: Pattern validation
# ---------------------------------------------------------------------------


def test_validate_patterns_valid():
    """Valid regex patterns should produce no errors."""
    patterns = [
        {"pattern": r"\btest\b", "category": "test"},
        {"pattern": r"[a-z]+@[a-z]+\.com", "category": "email"},
    ]
    errors = PIIDetectionService.validate_patterns(patterns)
    assert errors == []


def test_validate_patterns_invalid_regex():
    """Invalid regex patterns should return error messages."""
    patterns = [
        {"pattern": r"[invalid", "category": "broken"},
        {"pattern": r"\bvalid\b", "category": "ok"},
    ]
    errors = PIIDetectionService.validate_patterns(patterns)
    assert len(errors) == 1
    assert "[invalid" in errors[0]


def test_validate_patterns_multiple_invalid():
    """Multiple invalid patterns should all be reported."""
    patterns = [
        {"pattern": r"(unclosed", "category": "bad1"},
        {"pattern": r"[also_bad", "category": "bad2"},
    ]
    errors = PIIDetectionService.validate_patterns(patterns)
    assert len(errors) == 2


# ---------------------------------------------------------------------------
# Test: Anonymized alerts
# ---------------------------------------------------------------------------


def test_hash_user_id():
    """hash_user_id should return SHA-256 hex digest."""
    user_id = "user-123-abc"
    expected = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    assert PIIDetectionService.hash_user_id(user_id) == expected


def test_hash_user_id_deterministic():
    """Same user_id should always produce same hash."""
    uid = "test-user-456"
    h1 = PIIDetectionService.hash_user_id(uid)
    h2 = PIIDetectionService.hash_user_id(uid)
    assert h1 == h2


@pytest.mark.asyncio
async def test_check_pii_creates_anonymized_alert():
    """check_pii should create AgentActivity with hashed user_id, not actual."""
    service = PIIDetectionService()
    user_id = "user-real-id-789"
    settings = {}

    session = FakeSession([
        FakeScalarResult(settings),  # _load_patterns
        FakeScalarResult(settings),  # _apply_whitelist
    ])

    text = "Contact me at dev@acme.internal for questions."
    result = await service.check_pii(
        text=text, user_id=user_id, org_id="org-1", session=session
    )

    assert result.pii_detected is True
    assert "internal_email" in result.categories

    # Verify the alert was added to session
    assert len(session._added) == 1
    alert = session._added[0]

    # Alert data should have hashed_user_id, NOT actual user_id
    assert alert.data["hashed_user_id"] == PIIDetectionService.hash_user_id(user_id)
    assert "user-real-id-789" not in str(alert.data.get("hashed_user_id", ""))

    # Alert data should NOT contain matched text
    assert "dev@acme.internal" not in str(alert.data)

    # Alert should have correct event_type
    assert alert.event_type == "pii_detected"


@pytest.mark.asyncio
async def test_alert_does_not_contain_matched_text():
    """Anonymized alert metadata must NEVER contain the actual matched text."""
    service = PIIDetectionService()
    settings = {
        "pii_patterns": [
            {
                "pattern": r"\bSuperSecretProject\b",
                "category": "proprietary",
                "description": "Secret name",
                "enabled": True,
            }
        ],
    }

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "I was lead on SuperSecretProject for 2 years."
    result = await service.check_pii(
        text=text, user_id="user-1", org_id="org-1", session=session
    )

    assert result.pii_detected is True
    alert = session._added[0]
    alert_str = str(alert.data)

    # The matched text must NOT appear in alert data
    assert "SuperSecretProject" not in alert_str
    # But categories should be present
    assert "proprietary" in alert.data["categories"]


# ---------------------------------------------------------------------------
# Test: PII hook return values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_pii_returns_true_on_match():
    """check_pii should return pii_detected=True when patterns match."""
    service = PIIDetectionService()
    settings = {}

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "Refer to https://jira.company.com/browse/PROJ-123 for details."
    result = await service.check_pii(
        text=text, user_id="u1", org_id="org-1", session=session
    )

    assert result.pii_detected is True
    assert result.detection_count >= 1
    assert len(result.categories) >= 1


@pytest.mark.asyncio
async def test_check_pii_returns_false_on_no_match():
    """check_pii should return pii_detected=False when no patterns match."""
    service = PIIDetectionService()
    settings = {}

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "I have 5 years of Python experience and led a team of 8 engineers."
    result = await service.check_pii(
        text=text, user_id="u1", org_id="org-1", session=session
    )

    assert result.pii_detected is False
    assert result.detection_count == 0
    assert result.categories == []


@pytest.mark.asyncio
async def test_check_pii_no_alert_when_clean():
    """No AgentActivity should be created when no PII is detected."""
    service = PIIDetectionService()
    settings = {}

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    text = "Generic resume content with no PII."
    await service.check_pii(
        text=text, user_id="u1", org_id="org-1", session=session
    )

    assert len(session._added) == 0


# ---------------------------------------------------------------------------
# Test: RBAC enforcement (403 for non-admin)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pii_config_endpoint_requires_admin():
    """GET /admin/pii-config should return 403 for non-admin users."""
    from fastapi.testclient import TestClient

    from app.api.v1.admin_enterprise import router

    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Patch require_admin to raise 403
    with patch(
        "app.api.v1.admin_enterprise.require_admin",
        side_effect=lambda: (_ for _ in ()).throw(
            __import__("fastapi").HTTPException(status_code=403, detail="Admin access required.")
        ),
    ):
        # Re-register dependency override
        from app.auth.admin import require_admin as _ra

        async def fake_non_admin():
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Admin access required.")

        app.dependency_overrides[_ra] = fake_non_admin

        client = TestClient(app)
        response = client.get("/api/v1/admin/pii-config")
        assert response.status_code == 403

        response2 = client.get("/api/v1/admin/pii-alerts")
        assert response2.status_code == 403

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: Pattern CRUD via API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pii_config_put_validates_regex():
    """PUT /admin/pii-config should reject invalid regex patterns."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.v1.admin_enterprise import router
    from app.auth.admin import AdminContext, require_admin

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def fake_admin():
        return AdminContext(user_id="admin-1", org_id="org-1", org_name="Test Org")

    app.dependency_overrides[require_admin] = fake_admin

    client = TestClient(app)

    # Invalid regex should fail
    response = client.put(
        "/api/v1/admin/pii-config",
        json={
            "patterns": [
                {
                    "pattern": "[invalid_regex",
                    "category": "test",
                    "description": "Bad pattern",
                    "enabled": True,
                }
            ],
            "whitelist": [],
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert "errors" in body["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_pii_config_put_saves_valid_patterns():
    """PUT /admin/pii-config should save valid patterns and return them."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.v1.admin_enterprise import router
    from app.auth.admin import AdminContext, require_admin

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def fake_admin():
        return AdminContext(user_id="admin-1", org_id="org-1", org_name="Test Org")

    app.dependency_overrides[require_admin] = fake_admin

    # Mock the DB operations
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=FakeScalarResult({}))

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=None)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin)

    with patch("app.db.engine.AsyncSessionLocal", return_value=mock_session_ctx):
        client = TestClient(app)
        response = client.put(
            "/api/v1/admin/pii-config",
            json={
                "patterns": [
                    {
                        "pattern": r"\bProjectX\b",
                        "category": "code_name",
                        "description": "Secret project",
                        "enabled": True,
                    }
                ],
                "whitelist": ["safe_term"],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["patterns"]) == 1
    assert body["patterns"][0]["category"] == "code_name"
    assert body["whitelist"] == ["safe_term"]
    assert len(body["default_patterns"]) == len(DEFAULT_PATTERNS)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: No PII in empty text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_empty_text():
    """Scanning empty text should return no detections."""
    service = PIIDetectionService()
    settings = {}

    session = FakeSession([
        FakeScalarResult(settings),
        FakeScalarResult(settings),
    ])

    detections = await service.scan_text("", org_id="org-1", session=session)
    assert detections == []


# ---------------------------------------------------------------------------
# Test: Default patterns are well-formed
# ---------------------------------------------------------------------------


def test_default_patterns_all_compile():
    """All default patterns must be valid regexes."""
    errors = PIIDetectionService.validate_patterns(DEFAULT_PATTERNS)
    assert errors == [], f"Default patterns have errors: {errors}"


def test_default_patterns_have_required_fields():
    """Each default pattern must have pattern, category, enabled, id."""
    for pat in DEFAULT_PATTERNS:
        assert "pattern" in pat, f"Missing 'pattern': {pat}"
        assert "category" in pat, f"Missing 'category': {pat}"
        assert "enabled" in pat, f"Missing 'enabled': {pat}"
        assert "id" in pat, f"Missing 'id': {pat}"
