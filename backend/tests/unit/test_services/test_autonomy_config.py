"""Tests for per-employee autonomy configuration — Story 10-5."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.enterprise.autonomy_config import (
    LEVEL_ORDER,
    AutonomyConfigService,
    EmployeeAutonomyRequest,
    OrgAutonomyConfigResponse,
    OrgAutonomySettings,
    OrgRestrictions,
    RestrictionResult,
)


@pytest.fixture
def service():
    return AutonomyConfigService()


@pytest.fixture
def org_id():
    return str(uuid.uuid4())


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


class _FakeOrg:
    """Simple org stub that stores settings as a real dict."""

    def __init__(self, settings=None):
        self.settings = settings if settings is not None else {}
        self.id = uuid.uuid4()


def _make_org(settings=None):
    """Create a fake Organization with settings JSONB."""
    return _FakeOrg(settings=settings)


def _mock_session_with_org(org):
    """Create a mock AsyncSession that returns the given org on select."""
    session = AsyncMock()

    async def _execute(stmt):
        result = MagicMock()
        # Detect which query: Organization.settings (scalar) vs Organization (full)
        result.scalar_one_or_none = MagicMock(return_value=org.settings)
        result.scalar_one = MagicMock(return_value=org)
        return result

    session.execute = AsyncMock(side_effect=_execute)
    session.add = MagicMock()
    return session


# ── AC1: Organization default autonomy ─────────────────────────────────


class TestGetOrgAutonomyConfig:
    @pytest.mark.asyncio
    async def test_returns_defaults_for_new_org(self, service, org_id):
        """Test get_org_autonomy_config returns defaults when no config exists."""
        session = _mock_session_with_org(_make_org(settings={}))
        config = await service.get_org_autonomy_config(session, org_id)

        assert config.default_autonomy == "l1"
        assert config.max_autonomy == "l3"
        assert config.restrictions.blocked_companies == []
        assert config.restrictions.blocked_industries == []
        assert config.restrictions.require_approval_industries == []

    @pytest.mark.asyncio
    async def test_returns_defaults_when_settings_none(self, service, org_id):
        """Test get_org_autonomy_config returns defaults when settings is None."""
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=result)

        config = await service.get_org_autonomy_config(session, org_id)
        assert config.default_autonomy == "l1"
        assert config.max_autonomy == "l3"

    @pytest.mark.asyncio
    async def test_returns_stored_config(self, service, org_id):
        """Test get_org_autonomy_config reads from stored settings."""
        stored = {
            "autonomy": {
                "default_autonomy": "l2",
                "max_autonomy": "l2",
                "restrictions": {
                    "blocked_companies": ["BadCorp"],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))
        config = await service.get_org_autonomy_config(session, org_id)

        assert config.default_autonomy == "l2"
        assert config.max_autonomy == "l2"
        assert config.restrictions.blocked_companies == ["BadCorp"]


# ── AC1 continued: Update org autonomy config ──────────────────────────


class TestUpdateOrgAutonomyConfig:
    @pytest.mark.asyncio
    async def test_persists_values_to_settings(self, service, org_id):
        """Test update_org_autonomy_config persists values to settings JSONB."""
        org = _make_org(settings={})

        session = AsyncMock()
        # update_org_autonomy_config makes one DB call: select(Organization)
        result_mock = MagicMock()
        result_mock.scalar_one = MagicMock(return_value=org)
        session.execute = AsyncMock(return_value=result_mock)

        new_config = OrgAutonomySettings(
            default_autonomy="l2", max_autonomy="l3"
        )
        result = await service.update_org_autonomy_config(
            session, org_id, new_config
        )

        assert result.default_autonomy == "l2"
        assert result.max_autonomy == "l3"
        assert org.settings["autonomy"]["default_autonomy"] == "l2"

    @pytest.mark.asyncio
    async def test_rejects_default_exceeding_max(self, service, org_id):
        """Test update rejects config where default > max (e.g., default=L3, max=L1)."""
        session = AsyncMock()

        new_config = OrgAutonomySettings(
            default_autonomy="l3", max_autonomy="l1"
        )

        with pytest.raises(ValueError, match="cannot exceed"):
            await service.update_org_autonomy_config(
                session, org_id, new_config
            )


# ── AC2: Max autonomy ceiling enforcement ──────────────────────────────


class TestValidateEmployeeAutonomy:
    @pytest.mark.asyncio
    async def test_returns_false_when_exceeds_max(self, service, org_id):
        """Test validate_employee_autonomy returns False when requested > max."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l2",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.validate_employee_autonomy(
            session, org_id, "l3"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_within_max(self, service, org_id):
        """Test validate_employee_autonomy returns True when requested <= max."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.validate_employee_autonomy(
            session, org_id, "l2"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_equal_to_max(self, service, org_id):
        """Test validate_employee_autonomy returns True when requested == max."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l2",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.validate_employee_autonomy(
            session, org_id, "l2"
        )
        assert result is True


# ── AC3: Per-employee autonomy override ────────────────────────────────


class TestSetEmployeeAutonomy:
    @pytest.mark.asyncio
    async def test_caps_at_max_autonomy(self, service, org_id, user_id):
        """Test set_employee_autonomy caps at max_autonomy."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l2",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        org = _make_org(settings=stored)

        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count <= 1:
                # get_org_autonomy_config
                result.scalar_one_or_none = MagicMock(return_value=org.settings)
            else:
                # select UserPreference
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.add = MagicMock()

        effective = await service.set_employee_autonomy(
            session, org_id, user_id, "l3"
        )
        assert effective == "l2"  # capped at max

    @pytest.mark.asyncio
    async def test_allows_level_within_max(self, service, org_id, user_id):
        """Test set_employee_autonomy allows level within max."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        org = _make_org(settings=stored)

        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count <= 1:
                result.scalar_one_or_none = MagicMock(return_value=org.settings)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.add = MagicMock()

        effective = await service.set_employee_autonomy(
            session, org_id, user_id, "l2"
        )
        assert effective == "l2"


# ── AC4: Effective autonomy resolution ─────────────────────────────────


class TestGetEffectiveAutonomy:
    @pytest.mark.asyncio
    async def test_uses_org_default_when_no_user_pref(self, service, user_id):
        """Test get_effective_autonomy uses org default when no user pref."""
        org_id = uuid.uuid4()
        stored = {
            "autonomy": {
                "default_autonomy": "l2",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # UserPreference.autonomy_level
                result.scalar_one_or_none = MagicMock(return_value=None)
            elif call_count == 2:
                # OrganizationMember.org_id
                result.scalar_one_or_none = MagicMock(return_value=org_id)
            else:
                # Organization.settings
                result.scalar_one_or_none = MagicMock(return_value=stored)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)

        effective = await service.get_effective_autonomy(session, user_id)
        assert effective == "l2"

    @pytest.mark.asyncio
    async def test_caps_user_pref_at_org_max(self, service, user_id):
        """Test get_effective_autonomy caps user preference at org max."""
        org_id = uuid.uuid4()
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l2",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value="l3")
            elif call_count == 2:
                result.scalar_one_or_none = MagicMock(return_value=org_id)
            else:
                result.scalar_one_or_none = MagicMock(return_value=stored)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)

        effective = await service.get_effective_autonomy(session, user_id)
        assert effective == "l2"  # capped

    @pytest.mark.asyncio
    async def test_returns_user_pref_when_no_org(self, service, user_id):
        """Test get_effective_autonomy returns user pref when no org membership."""
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value="l2")
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)

        effective = await service.get_effective_autonomy(session, user_id)
        assert effective == "l2"

    @pytest.mark.asyncio
    async def test_returns_l0_when_no_org_no_pref(self, service, user_id):
        """Test get_effective_autonomy returns l0 when no org and no pref."""
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)

        effective = await service.get_effective_autonomy(session, user_id)
        assert effective == "l0"

    @pytest.mark.asyncio
    async def test_user_pref_within_max_is_honored(self, service, user_id):
        """Test user preference is honored when within org max."""
        org_id = uuid.uuid4()
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value="l2")
            elif call_count == 2:
                result.scalar_one_or_none = MagicMock(return_value=org_id)
            else:
                result.scalar_one_or_none = MagicMock(return_value=stored)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)

        effective = await service.get_effective_autonomy(session, user_id)
        assert effective == "l2"


# ── AC5/AC6: Restrictions ──────────────────────────────────────────────


class TestCheckRestrictions:
    @pytest.mark.asyncio
    async def test_blocks_company_in_blocked_list(self, service, org_id):
        """Test check_restrictions blocks company in blocked_companies list."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": ["EvilCorp", "BadInc"],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.check_restrictions(
            session, org_id, company="EvilCorp"
        )
        assert result.blocked is True
        assert result.requires_approval is False
        assert "EvilCorp" in result.reason

    @pytest.mark.asyncio
    async def test_blocks_industry_in_blocked_list(self, service, org_id):
        """Test check_restrictions blocks industry in blocked_industries."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": ["Tobacco", "Gambling"],
                    "require_approval_industries": [],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.check_restrictions(
            session, org_id, industry="Tobacco"
        )
        assert result.blocked is True
        assert "Tobacco" in result.reason

    @pytest.mark.asyncio
    async def test_requires_approval_for_industry(self, service, org_id):
        """Test check_restrictions requires approval for industry in require_approval_industries."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": [],
                    "blocked_industries": [],
                    "require_approval_industries": ["Defense", "Finance"],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.check_restrictions(
            session, org_id, industry="Defense"
        )
        assert result.blocked is False
        assert result.requires_approval is True
        assert "Defense" in result.reason

    @pytest.mark.asyncio
    async def test_no_restrictions_when_clean(self, service, org_id):
        """Test check_restrictions returns no restrictions for non-restricted company/industry."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": ["EvilCorp"],
                    "blocked_industries": ["Tobacco"],
                    "require_approval_industries": ["Defense"],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.check_restrictions(
            session, org_id, company="GoodCorp", industry="Technology"
        )
        assert result.blocked is False
        assert result.requires_approval is False
        assert result.reason == ""

    @pytest.mark.asyncio
    async def test_case_insensitive_company_matching(self, service, org_id):
        """Test that company restriction matching is case-insensitive."""
        stored = {
            "autonomy": {
                "default_autonomy": "l1",
                "max_autonomy": "l3",
                "restrictions": {
                    "blocked_companies": ["EvilCorp"],
                    "blocked_industries": [],
                    "require_approval_industries": [],
                },
            }
        }
        session = _mock_session_with_org(_make_org(settings=stored))

        result = await service.check_restrictions(
            session, org_id, company="evilcorp"
        )
        assert result.blocked is True


# ── AC6: Org restriction checker for agents (non-org user) ─────────────


class TestOrgRestrictionsChecker:
    @pytest.mark.asyncio
    async def test_no_restrictions_for_non_org_user(self):
        """Test check_org_restrictions returns no restrictions for non-org user."""
        from app.agents.org_restrictions import check_org_restrictions

        user_id = str(uuid.uuid4())

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=result_mock)

        # Mock AsyncSessionLocal context manager
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.db.engine.AsyncSessionLocal",
            return_value=mock_session_ctx,
        ):
            result = await check_org_restrictions(
                user_id, company="AnyCompany", industry="AnyIndustry"
            )

        assert result.blocked is False
        assert result.requires_approval is False
        assert result.reason == ""


# ── Pydantic model validation ──────────────────────────────────────────


class TestPydanticModels:
    def test_org_autonomy_settings_validates_levels(self):
        """Test OrgAutonomySettings rejects invalid levels."""
        with pytest.raises(ValueError):
            OrgAutonomySettings(default_autonomy="l5", max_autonomy="l3")

    def test_org_autonomy_settings_lowercases(self):
        """Test OrgAutonomySettings lowercases level strings."""
        config = OrgAutonomySettings(default_autonomy="L1", max_autonomy="L3")
        assert config.default_autonomy == "l1"
        assert config.max_autonomy == "l3"

    def test_employee_autonomy_request_validates(self):
        """Test EmployeeAutonomyRequest rejects invalid levels."""
        with pytest.raises(ValueError):
            EmployeeAutonomyRequest(level="l9")

    def test_employee_autonomy_request_allows_l0(self):
        """Test EmployeeAutonomyRequest allows l0 (employees can choose l0)."""
        req = EmployeeAutonomyRequest(level="l0")
        assert req.level == "l0"

    def test_org_restrictions_defaults(self):
        """Test OrgRestrictions has empty list defaults."""
        r = OrgRestrictions()
        assert r.blocked_companies == []
        assert r.blocked_industries == []
        assert r.require_approval_industries == []

    def test_org_autonomy_config_response(self):
        """Test OrgAutonomyConfigResponse serializes correctly."""
        resp = OrgAutonomyConfigResponse(
            default_autonomy="l1",
            max_autonomy="l3",
            restrictions=OrgRestrictions(blocked_companies=["X"]),
        )
        data = resp.model_dump()
        assert data["default_autonomy"] == "l1"
        assert data["restrictions"]["blocked_companies"] == ["X"]

    def test_restriction_result_dataclass(self):
        """Test RestrictionResult dataclass creation."""
        r = RestrictionResult(blocked=True, requires_approval=False, reason="test")
        assert r.blocked is True
        assert r.requires_approval is False
        assert r.reason == "test"


# ── AC7: Audit logging (API layer) ────────────────────────────────────


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_update_config_logs_audit_event(self, service, org_id):
        """Test that autonomy config changes would trigger audit logging.

        The actual audit logging is tested at the API layer. Here we verify
        the service correctly returns before/after values needed for audit.
        """
        org = _make_org(settings={})

        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=org.settings)
            else:
                result.scalar_one = MagicMock(return_value=org)
                result.scalar_one_or_none = MagicMock(return_value=org.settings)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)

        new_config = OrgAutonomySettings(
            default_autonomy="l2", max_autonomy="l3"
        )
        result = await service.update_org_autonomy_config(
            session, org_id, new_config
        )

        # Verify result contains data suitable for audit log changes JSONB
        result_dict = result.model_dump()
        assert "default_autonomy" in result_dict
        assert "max_autonomy" in result_dict
        assert "restrictions" in result_dict
