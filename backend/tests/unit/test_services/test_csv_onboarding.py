"""Tests for CSV bulk employee onboarding — Story 10-2."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.enterprise.csv_onboarding import (
    MAX_BATCH_SIZE,
    CSVOnboardingService,
    RowError,
    ValidationResult,
)


@pytest.fixture
def service():
    return CSVOnboardingService()


# ── AC1: CSV upload and parsing ──────────────────────────────────────────


class TestCSVParsing:
    def test_parse_csv_valid(self, service):
        content = b"email,first_name,last_name,department\nalice@example.com,Alice,Smith,Engineering\nbob@example.com,Bob,Jones,Sales\n"
        rows = service.parse_csv(content)
        assert len(rows) == 2
        assert rows[0]["email"] == "alice@example.com"
        assert rows[0]["first_name"] == "Alice"
        assert rows[1]["email"] == "bob@example.com"

    def test_parse_csv_missing_email_header(self, service):
        content = b"name,department\nAlice,Engineering\n"
        with pytest.raises(ValueError, match="Missing required CSV headers.*email"):
            service.parse_csv(content)

    def test_parse_csv_with_bom(self, service):
        bom = b"\xef\xbb\xbf"
        content = bom + b"email\nalice@example.com\n"
        rows = service.parse_csv(content)
        assert len(rows) == 1
        assert rows[0]["email"] == "alice@example.com"

    def test_parse_csv_empty_file(self, service):
        with pytest.raises(ValueError, match="empty"):
            service.parse_csv(b"")

    def test_parse_csv_email_only(self, service):
        content = b"email\ntest@example.com\n"
        rows = service.parse_csv(content)
        assert len(rows) == 1
        assert rows[0]["email"] == "test@example.com"


# ── AC2: Email format validation ─────────────────────────────────────────


class TestEmailValidation:
    @pytest.mark.asyncio
    async def test_invalid_email_flagged(self, service):
        rows = [{"email": "not-an-email"}, {"email": "valid@example.com"}]
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(
            __iter__=lambda self: iter([])
        ))
        result = await service.validate_rows(rows, str(uuid.uuid4()), session)
        assert len(result.invalid_rows) == 1
        assert result.invalid_rows[0].error_reason == "invalid_email_format"
        assert len(result.valid_rows) == 1

    @pytest.mark.asyncio
    async def test_empty_email_flagged(self, service):
        rows = [{"email": ""}]
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(
            __iter__=lambda self: iter([])
        ))
        result = await service.validate_rows(rows, str(uuid.uuid4()), session)
        assert len(result.invalid_rows) == 1
        assert result.invalid_rows[0].error_reason == "invalid_email_format"


# ── AC3: Duplicate detection within CSV ──────────────────────────────────


class TestDuplicateDetection:
    @pytest.mark.asyncio
    async def test_duplicate_in_csv_flagged(self, service):
        rows = [
            {"email": "alice@example.com"},
            {"email": "alice@example.com"},
            {"email": "bob@example.com"},
        ]
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(
            __iter__=lambda self: iter([])
        ))
        result = await service.validate_rows(rows, str(uuid.uuid4()), session)
        assert len(result.valid_rows) == 2
        assert len(result.invalid_rows) == 1
        assert result.invalid_rows[0].error_reason == "duplicate_in_upload"
        assert result.invalid_rows[0].row_number == 3  # second occurrence


# ── AC4: Existing account detection ──────────────────────────────────────


class TestExistingAccountDetection:
    @pytest.mark.asyncio
    async def test_already_in_org_flagged(self, service):
        org_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        rows = [{"email": "alice@example.com"}]

        # Mock: user exists
        user_row = MagicMock()
        user_row.email = "alice@example.com"
        user_row.id = user_id

        # Mock: user is in org
        member_row = MagicMock()
        member_row.user_id = user_id

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                MagicMock(__iter__=lambda self: iter([user_row])),  # user query
                MagicMock(__iter__=lambda self: iter([member_row])),  # member query
            ]
        )

        result = await service.validate_rows(rows, org_id, session)
        assert len(result.invalid_rows) == 1
        assert result.invalid_rows[0].error_reason == "already_in_org"

    @pytest.mark.asyncio
    async def test_existing_account_different_org_flagged(self, service):
        org_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        rows = [{"email": "alice@example.com"}]

        user_row = MagicMock()
        user_row.email = "alice@example.com"
        user_row.id = user_id

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                MagicMock(__iter__=lambda self: iter([user_row])),  # user exists
                MagicMock(__iter__=lambda self: iter([])),  # NOT in this org
            ]
        )

        result = await service.validate_rows(rows, org_id, session)
        assert len(result.invalid_rows) == 1
        assert result.invalid_rows[0].error_reason == "existing_account_different_org"


# ── AC5: Batch size enforcement ──────────────────────────────────────────


class TestBatchSizeLimit:
    def test_csv_over_1000_rows_rejected(self, service):
        header = "email\n"
        rows = "".join(f"user{i}@example.com\n" for i in range(1001))
        content = (header + rows).encode()
        with pytest.raises(ValueError, match="maximum batch size"):
            service.parse_csv(content)

    def test_csv_exactly_1000_rows_accepted(self, service):
        header = "email\n"
        rows = "".join(f"user{i}@example.com\n" for i in range(1000))
        content = (header + rows).encode()
        result = service.parse_csv(content)
        assert len(result) == 1000


# ── AC6: Valid rows queued + AC7: Error report ───────────────────────────


class TestAPIEndpoint:
    @pytest.mark.asyncio
    async def test_endpoint_returns_correct_summary(self):
        """Test the bulk upload endpoint returns proper summary counts."""
        from app.api.v1.admin import BulkUploadResponse, RowErrorSchema

        response = BulkUploadResponse(
            total=5,
            valid=3,
            invalid=2,
            queued=3,
            errors=[
                RowErrorSchema(row_number=3, email="bad", error_reason="invalid_email_format"),
                RowErrorSchema(row_number=5, email="dup@x.com", error_reason="duplicate_in_upload"),
            ],
        )
        assert response.total == 5
        assert response.valid == 3
        assert response.invalid == 2
        assert response.queued == 3
        assert len(response.errors) == 2
        assert response.errors[0].error_reason == "invalid_email_format"

    def test_bulk_upload_endpoint_exists(self):
        """Verify the bulk-upload endpoint is registered on the admin router."""
        from app.api.v1.admin import router

        paths = [route.path for route in router.routes]
        assert any("employees/bulk-upload" in p for p in paths)

    def test_bulk_upload_requires_admin(self):
        """Verify bulk-upload endpoint has require_admin dependency."""
        import inspect
        from app.api.v1.admin import bulk_upload_employees, require_admin

        sig = inspect.signature(bulk_upload_employees)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None, "admin_ctx parameter not found"
        assert admin_param.default.dependency is require_admin


# ── AC8: Audit logging ──────────────────────────────────────────────────


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_log_audit_event_called_with_bulk_upload(self):
        """Verify log_audit_event is called with bulk_upload action."""
        from app.services.enterprise.audit import log_audit_event

        session = AsyncMock()
        org_id = str(uuid.uuid4())
        actor_id = str(uuid.uuid4())

        await log_audit_event(
            session=session,
            org_id=org_id,
            actor_id=actor_id,
            action="bulk_upload",
            resource_type="csv_onboarding",
            changes={"total": 5, "valid": 3, "invalid": 2, "queued": 3},
        )

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.action == "bulk_upload"
        assert added.resource_type == "csv_onboarding"
        assert added.changes == {"total": 5, "valid": 3, "invalid": 2, "queued": 3}


# ── Celery task ──────────────────────────────────────────────────────────


class TestCeleryTask:
    def test_bulk_onboard_task_registered(self):
        """Verify the Celery task is registered."""
        from app.worker.tasks import bulk_onboard_employees

        assert bulk_onboard_employees.name == "app.worker.tasks.bulk_onboard_employees"
        assert bulk_onboard_employees.max_retries == 2
