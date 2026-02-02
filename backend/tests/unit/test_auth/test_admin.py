"""
Tests for Story 10-1: Enterprise Admin Role and Permissions.

Validates:
  AC1 - Organization + OrganizationMember models with correct fields
  AC2 - require_admin dependency resolves for admin users
  AC3 - require_admin raises 403 for non-admin users
  AC4 - AuditLog records persisted for admin write actions
  AC5 - RLS org-scoped data isolation
  AC6 - Admin cannot see individual application/pipeline data
  AC7 - Existing admin routes migrated to RBAC

Uses unittest.mock for all DB interactions -- no running database required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import (
    AuditLog,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
)


# ============================================================
# AC1 - Organization Model Fields
# ============================================================


class TestOrganizationModelFields:
    """AC1: Organization model has all required columns."""

    def test_organization_model_fields(self):
        """Organization has id, name, logo_url, settings, created_at, updated_at, deleted_at."""
        columns = {c.name for c in Organization.__table__.columns}
        expected = {
            "id", "name", "logo_url", "settings",
            "created_at", "updated_at", "deleted_at",
        }
        assert expected.issubset(columns), (
            f"Missing columns: {expected - columns}"
        )


class TestOrganizationMemberModelFields:
    """AC1: OrganizationMember model has all required columns."""

    def test_organization_member_model_fields(self):
        """OrganizationMember has id, org_id, user_id, role, created_at, updated_at."""
        columns = {c.name for c in OrganizationMember.__table__.columns}
        expected = {"id", "org_id", "user_id", "role", "created_at", "updated_at"}
        assert expected.issubset(columns), (
            f"Missing columns: {expected - columns}"
        )


class TestOrgRoleEnum:
    """AC1: OrgRole enum has correct values."""

    def test_org_role_enum_values(self):
        """OrgRole.ADMIN == 'admin' and OrgRole.MEMBER == 'member'."""
        assert OrgRole.ADMIN == "admin"
        assert OrgRole.ADMIN.value == "admin"
        assert OrgRole.MEMBER == "member"
        assert OrgRole.MEMBER.value == "member"


class TestUserOrgIdField:
    """AC1: User model has org_id column."""

    def test_user_org_id_field(self):
        """User model has org_id column."""
        columns = {c.name for c in User.__table__.columns}
        assert "org_id" in columns, "User model missing org_id column"

    def test_user_org_id_references_organizations(self):
        """User.org_id foreign key references organizations.id."""
        org_id_col = User.__table__.columns["org_id"]
        fk_targets = {str(fk.column) for fk in org_id_col.foreign_keys}
        assert "organizations.id" in fk_targets


# ============================================================
# AC2 - require_admin Returns AdminContext
# ============================================================


class TestRequireAdminReturnsContext:
    """AC2: require_admin resolves for admin users."""

    @pytest.mark.asyncio
    async def test_require_admin_returns_admin_context(self):
        """Mock DB query returning admin membership -> returns AdminContext."""
        from app.auth.admin import AdminContext, require_admin

        test_user_id = str(uuid4())
        test_org_id = str(uuid4())
        test_org_name = "Test Corp"

        # Create mock OrganizationMember and Organization
        mock_member = MagicMock(spec=OrganizationMember)
        mock_member.user_id = test_user_id
        mock_member.org_id = test_org_id

        mock_org = MagicMock(spec=Organization)
        mock_org.name = test_org_name

        # Mock the row returned by result.first()
        mock_row = MagicMock()
        mock_row.__iter__ = MagicMock(return_value=iter([mock_member, mock_org]))
        mock_row.__getitem__ = MagicMock(side_effect=lambda i: [mock_member, mock_org][i])

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock AsyncSessionLocal as async context manager
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.auth.admin.AsyncSessionLocal", return_value=mock_session_ctx):
            ctx = await require_admin(user_id=test_user_id)

        assert isinstance(ctx, AdminContext)
        assert ctx.user_id == test_user_id
        assert ctx.org_id == test_org_id
        assert ctx.org_name == test_org_name


# ============================================================
# AC3 - require_admin Rejects Non-Admin Users
# ============================================================


class TestRequireAdminRejection:
    """AC3: require_admin raises 403 for non-admin/no-membership."""

    @pytest.mark.asyncio
    async def test_require_admin_raises_403_for_member_role(self):
        """DB query returning no admin membership -> 403."""
        from app.auth.admin import require_admin

        mock_result = MagicMock()
        mock_result.first.return_value = None  # No admin membership found

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.auth.admin.AsyncSessionLocal", return_value=mock_session_ctx):
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(user_id=str(uuid4()))

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_raises_403_for_no_membership(self):
        """DB query returning None (no membership at all) -> 403."""
        from app.auth.admin import require_admin

        mock_result = MagicMock()
        mock_result.first.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.auth.admin.AsyncSessionLocal", return_value=mock_session_ctx):
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(user_id=str(uuid4()))

        assert exc_info.value.status_code == 403


# ============================================================
# AC4 - Audit Log
# ============================================================


class TestAuditLog:
    """AC4: AuditLog records persisted for admin write actions."""

    @pytest.mark.asyncio
    async def test_log_audit_event_creates_record(self):
        """log_audit_event calls session.add with an AuditLog instance."""
        from app.services.enterprise.audit import log_audit_event

        mock_session = AsyncMock()
        test_org_id = str(uuid4())
        test_actor_id = str(uuid4())
        test_resource_id = str(uuid4())

        await log_audit_event(
            session=mock_session,
            org_id=test_org_id,
            actor_id=test_actor_id,
            action="invite_employee",
            resource_type="organization_member",
            resource_id=test_resource_id,
            changes={"role": "member"},
        )

        mock_session.add.assert_called_once()
        added_obj = mock_session.add.call_args[0][0]
        assert isinstance(added_obj, AuditLog)
        assert added_obj.action == "invite_employee"
        assert added_obj.resource_type == "organization_member"
        assert added_obj.changes == {"role": "member"}

    def test_audit_log_model_fields(self):
        """AuditLog has id, org_id, actor_id, action, resource_type, resource_id, changes, created_at."""
        columns = {c.name for c in AuditLog.__table__.columns}
        expected = {
            "id", "org_id", "actor_id", "action",
            "resource_type", "resource_id", "changes", "created_at",
        }
        assert expected.issubset(columns), (
            f"Missing columns: {expected - columns}"
        )


# ============================================================
# AC5 - RLS Org-Scoped Isolation
# ============================================================


class TestOrgRLSContext:
    """AC5: set_org_rls_context sets variable and validates UUID."""

    @pytest.mark.asyncio
    async def test_set_org_rls_context_sets_variable(self):
        """set_org_rls_context issues SET LOCAL app.current_org_id."""
        from app.db.rls import set_org_rls_context

        mock_session = AsyncMock()
        test_org_id = "12345678-1234-1234-1234-123456789abc"

        await set_org_rls_context(mock_session, test_org_id)

        mock_session.execute.assert_called_once()
        executed_sql = str(mock_session.execute.call_args[0][0])
        assert "SET LOCAL app.current_org_id" in executed_sql
        assert test_org_id in executed_sql

    @pytest.mark.asyncio
    async def test_set_org_rls_context_validates_uuid(self):
        """set_org_rls_context raises ValueError for non-UUID strings."""
        from app.db.rls import set_org_rls_context

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid org_id"):
            await set_org_rls_context(mock_session, "not-a-uuid")


# ============================================================
# AC6 - Admin Endpoints Do Not Expose User Data
# ============================================================


class TestAdminEndpointPrivacy:
    """AC6: Admin cannot see individual application/pipeline data."""

    def test_admin_endpoints_do_not_expose_user_applications(self):
        """No admin route path includes applications, pipelines, matches, or resumes."""
        from app.api.v1.admin import router

        forbidden_segments = {"applications", "pipelines", "matches", "resumes"}
        for route in router.routes:
            path = getattr(route, "path", "")
            path_segments = set(path.strip("/").split("/"))
            overlap = path_segments & forbidden_segments
            assert not overlap, (
                f"Admin route '{path}' exposes user data via segment(s): {overlap}"
            )


# ============================================================
# AC7 - Existing Admin Routes Migrated to RBAC
# ============================================================


class TestRBACMigration:
    """AC7: Existing admin routes require require_admin dependency."""

    def test_llm_costs_requires_admin(self):
        """get_llm_costs endpoint has require_admin in its dependencies."""
        from app.api.v1.admin import get_llm_costs

        # Inspect the FastAPI dependency annotations
        import inspect

        sig = inspect.signature(get_llm_costs)
        param_names = list(sig.parameters.keys())
        # The admin_ctx parameter should exist with Depends(require_admin)
        assert "admin_ctx" in param_names, (
            "get_llm_costs is missing admin_ctx parameter (require_admin dependency)"
        )

        # Verify the default is a Depends on require_admin
        param = sig.parameters["admin_ctx"]
        from fastapi import Depends
        from app.auth.admin import require_admin

        assert param.default is not None
        assert hasattr(param.default, "dependency"), (
            "admin_ctx default is not a FastAPI Depends"
        )
        assert param.default.dependency is require_admin

    def test_dlq_requires_admin(self):
        """get_dlq endpoint has require_admin in its dependencies."""
        from app.api.v1.admin import get_dlq

        import inspect

        sig = inspect.signature(get_dlq)
        param_names = list(sig.parameters.keys())

        # Check that the endpoint has admin_ctx parameter
        # Note: The current get_dlq may not have this yet -- AC7 requires it.
        # If it's missing, the test correctly fails (indicating RBAC not wired).
        assert "admin_ctx" in param_names, (
            "get_dlq is missing admin_ctx parameter (require_admin dependency)"
        )

        param = sig.parameters["admin_ctx"]
        from app.auth.admin import require_admin

        assert param.default is not None
        assert hasattr(param.default, "dependency"), (
            "admin_ctx default is not a FastAPI Depends"
        )
        assert param.default.dependency is require_admin
