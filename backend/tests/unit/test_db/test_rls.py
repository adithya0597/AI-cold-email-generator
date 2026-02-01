"""
Tests for Story 0.2: Row-Level Security Policies.

Validates:
  AC1 - RLS enabled on all 8 user-scoped tables
  AC2 - User isolation policy on each table
  AC3 - Development bypass policy on each table
  AC4 - Backend rls.py helper issues correct SQL
  AC5 - Rollback migration removes all policies and RLS
  AC6 - Policy existence and naming conventions

Uses SQL file parsing (reads .sql files and verifies content)
rather than running against a live database.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call

import pytest

# ============================================================
# Constants
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"

RLS_TABLES = [
    "profiles",
    "applications",
    "matches",
    "documents",
    "agent_actions",
    "agent_outputs",
    "swipe_events",
    "learned_preferences",
]


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def forward_sql() -> str:
    """Load the RLS forward migration SQL."""
    path = MIGRATIONS_DIR / "00003_row_level_security.sql"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def rollback_sql() -> str:
    """Load the RLS rollback migration SQL."""
    path = MIGRATIONS_DIR / "00003_row_level_security_rollback.sql"
    return path.read_text(encoding="utf-8")


# ============================================================
# AC1 - RLS Enabled on All Tables
# ============================================================


class TestRLSEnabled:
    """AC1: RLS is enabled on all 8 user-scoped tables."""

    def test_forward_migration_file_exists(self):
        """Forward migration file exists and is readable."""
        path = MIGRATIONS_DIR / "00003_row_level_security.sql"
        assert path.exists(), f"Migration file not found: {path}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 0, "Migration file is empty"

    def test_rollback_migration_file_exists(self):
        """Rollback migration file exists and is readable."""
        path = MIGRATIONS_DIR / "00003_row_level_security_rollback.sql"
        assert path.exists(), f"Rollback file not found: {path}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 0, "Rollback file is empty"

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_rls_enabled_on_table(self, table: str, forward_sql: str):
        """Each user-scoped table has ENABLE ROW LEVEL SECURITY."""
        expected = f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"
        assert expected in forward_sql, (
            f"Missing ENABLE ROW LEVEL SECURITY for {table}"
        )

    def test_rls_enabled_count(self, forward_sql: str):
        """Exactly 8 ENABLE ROW LEVEL SECURITY statements exist."""
        count = forward_sql.count("ENABLE ROW LEVEL SECURITY")
        assert count == 8, f"Expected 8 ENABLE RLS statements, found {count}"


# ============================================================
# AC2 - User Isolation Policies
# ============================================================


class TestUserIsolationPolicies:
    """AC2: User isolation policy on each table using current_setting."""

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_user_isolation_policy_exists(self, table: str, forward_sql: str):
        """Each table has a user_isolation_policy."""
        expected = f"CREATE POLICY user_isolation_policy ON {table}"
        assert expected in forward_sql, (
            f"Missing user_isolation_policy for {table}"
        )

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_user_isolation_uses_current_setting(self, table: str, forward_sql: str):
        """User isolation policies use current_setting with true arg."""
        assert "current_setting('app.current_user_id', true)::uuid" in forward_sql

    def test_user_isolation_policy_count(self, forward_sql: str):
        """Exactly 8 user_isolation_policy CREATE statements exist."""
        count = forward_sql.count("CREATE POLICY user_isolation_policy ON")
        assert count == 8, f"Expected 8 user_isolation policies, found {count}"

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_user_isolation_is_for_all(self, table: str, forward_sql: str):
        """User isolation policies apply FOR ALL operations."""
        # Find the policy block for this table
        policy_marker = f"CREATE POLICY user_isolation_policy ON {table}"
        idx = forward_sql.index(policy_marker)
        # Check FOR ALL appears in the next few lines after the policy name
        policy_block = forward_sql[idx:idx + 200]
        assert "FOR ALL" in policy_block, (
            f"user_isolation_policy on {table} is not FOR ALL"
        )


# ============================================================
# AC3 - Development Bypass Policies
# ============================================================


class TestDevBypassPolicies:
    """AC3: Development bypass policy with environment safeguards."""

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_dev_bypass_policy_exists(self, table: str, forward_sql: str):
        """Each table has a dev_bypass_policy."""
        expected = f"CREATE POLICY dev_bypass_policy ON {table}"
        assert expected in forward_sql, (
            f"Missing dev_bypass_policy for {table}"
        )

    def test_dev_bypass_policy_count(self, forward_sql: str):
        """Exactly 8 dev_bypass_policy CREATE statements exist."""
        count = forward_sql.count("CREATE POLICY dev_bypass_policy ON")
        assert count == 8, f"Expected 8 dev_bypass policies, found {count}"

    def test_dev_bypass_requires_environment_check(self, forward_sql: str):
        """Dev bypass requires app.environment = 'development'."""
        assert "current_setting('app.environment', true) = 'development'" in forward_sql

    def test_dev_bypass_requires_rls_bypass_flag(self, forward_sql: str):
        """Dev bypass requires app.rls_bypass = 'true'."""
        assert "current_setting('app.rls_bypass', true) = 'true'" in forward_sql

    def test_dev_bypass_requires_both_conditions(self, forward_sql: str):
        """Dev bypass uses AND to require both conditions."""
        # Both conditions must appear together with AND
        assert "app.environment" in forward_sql
        assert "app.rls_bypass" in forward_sql
        # The AND keyword must connect them
        assert "AND" in forward_sql


# ============================================================
# AC4 - Backend RLS Context Helper
# ============================================================


class TestSetRLSContext:
    """AC4: Backend rls.py helper issues correct SET LOCAL statement."""

    def test_rls_module_importable(self):
        """rls module can be imported."""
        from app.db.rls import set_rls_context
        assert callable(set_rls_context)

    @pytest.mark.asyncio
    async def test_set_rls_context_executes_set_local(self):
        """set_rls_context issues SET LOCAL with the user_id."""
        from app.db.rls import set_rls_context

        mock_session = AsyncMock()
        user_id = "12345678-1234-1234-1234-123456789abc"

        await set_rls_context(mock_session, user_id)

        mock_session.execute.assert_called_once()
        executed_sql = str(mock_session.execute.call_args[0][0])
        assert "SET LOCAL app.current_user_id" in executed_sql
        assert user_id in executed_sql

    @pytest.mark.asyncio
    async def test_set_rls_context_rejects_invalid_uuid(self):
        """set_rls_context raises ValueError for non-UUID strings."""
        from app.db.rls import set_rls_context

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid user_id"):
            await set_rls_context(mock_session, "not-a-uuid")

    @pytest.mark.asyncio
    async def test_set_rls_context_rejects_sql_injection(self):
        """set_rls_context rejects strings with SQL injection attempts."""
        from app.db.rls import set_rls_context

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid user_id"):
            await set_rls_context(mock_session, "'; DROP TABLE users; --")

    @pytest.mark.asyncio
    async def test_set_rls_context_rejects_empty_string(self):
        """set_rls_context rejects empty string."""
        from app.db.rls import set_rls_context

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid user_id"):
            await set_rls_context(mock_session, "")

    @pytest.mark.asyncio
    async def test_set_rls_context_rejects_non_string(self):
        """set_rls_context rejects non-string input."""
        from app.db.rls import set_rls_context

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid user_id"):
            await set_rls_context(mock_session, 12345)

    @pytest.mark.asyncio
    async def test_set_rls_context_accepts_uppercase_uuid(self):
        """set_rls_context accepts uppercase UUID strings."""
        from app.db.rls import set_rls_context

        mock_session = AsyncMock()
        user_id = "ABCDEF12-3456-7890-ABCD-EF1234567890"

        await set_rls_context(mock_session, user_id)
        mock_session.execute.assert_called_once()


# ============================================================
# AC5 - Rollback Migration
# ============================================================


class TestRollbackMigration:
    """AC5: Rollback migration cleanly removes all policies and RLS."""

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_rollback_drops_user_isolation_policy(self, table: str, rollback_sql: str):
        """Rollback drops user_isolation_policy for each table."""
        expected = f"DROP POLICY IF EXISTS user_isolation_policy ON {table}"
        assert expected in rollback_sql, (
            f"Missing DROP user_isolation_policy for {table}"
        )

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_rollback_drops_dev_bypass_policy(self, table: str, rollback_sql: str):
        """Rollback drops dev_bypass_policy for each table."""
        expected = f"DROP POLICY IF EXISTS dev_bypass_policy ON {table}"
        assert expected in rollback_sql, (
            f"Missing DROP dev_bypass_policy for {table}"
        )

    @pytest.mark.parametrize("table", RLS_TABLES)
    def test_rollback_disables_rls(self, table: str, rollback_sql: str):
        """Rollback disables RLS for each table."""
        expected = f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"
        assert expected in rollback_sql, (
            f"Missing DISABLE ROW LEVEL SECURITY for {table}"
        )

    def test_rollback_drop_policy_count(self, rollback_sql: str):
        """Rollback drops exactly 16 policies (2 per table x 8 tables)."""
        count = rollback_sql.count("DROP POLICY IF EXISTS")
        assert count == 16, f"Expected 16 DROP POLICY statements, found {count}"

    def test_rollback_disable_rls_count(self, rollback_sql: str):
        """Rollback disables RLS on exactly 8 tables."""
        count = rollback_sql.count("DISABLE ROW LEVEL SECURITY")
        assert count == 8, f"Expected 8 DISABLE RLS statements, found {count}"

    def test_rollback_drops_policies_before_disabling_rls(self, rollback_sql: str):
        """Policies are dropped before RLS is disabled (order matters)."""
        last_drop = rollback_sql.rfind("DROP POLICY IF EXISTS")
        first_disable = rollback_sql.find("DISABLE ROW LEVEL SECURITY")
        assert last_drop < first_disable, (
            "DROP POLICY statements should come before DISABLE RLS statements"
        )


# ============================================================
# AC6 - Policy Naming Conventions
# ============================================================


class TestPolicyNamingConventions:
    """AC6: Policy names follow established conventions."""

    def test_user_isolation_policy_naming(self, forward_sql: str):
        """All user isolation policies use consistent naming."""
        for table in RLS_TABLES:
            assert f"user_isolation_policy ON {table}" in forward_sql

    def test_dev_bypass_policy_naming(self, forward_sql: str):
        """All dev bypass policies use consistent naming."""
        for table in RLS_TABLES:
            assert f"dev_bypass_policy ON {table}" in forward_sql

    def test_no_tables_without_rls_excluded(self, forward_sql: str):
        """Users and jobs tables are NOT included (not user-scoped for RLS)."""
        assert "ALTER TABLE users ENABLE ROW LEVEL SECURITY" not in forward_sql
        assert "ALTER TABLE jobs ENABLE ROW LEVEL SECURITY" not in forward_sql
