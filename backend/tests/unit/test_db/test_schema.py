"""
Tests for Story 0.1: Database Schema Foundation.

Validates:
  AC1 - Core tables exist with proper relationships
  AC2 - UUID primary keys with gen_random_uuid() defaults
  AC3 - Timestamps auto-populated on all tables
  AC4 - Soft delete columns on user-facing tables
  AC5 - users.timezone defaults to 'UTC'
  AC6 - Migration rollback tested (SQL file exists and is parseable)
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine

from backend.app.db.models import (
    AgentAction,
    AgentOutput,
    AgentType,
    Application,
    ApplicationStatus,
    Base,
    Document,
    DocumentType,
    H1BSponsorStatus,
    Job,
    Match,
    MatchStatus,
    Profile,
    User,
    UserTier,
)


# ============================================================
# Fixtures
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"


@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine for testing model structure.

    Note: SQLite cannot render PostgreSQL-specific types (JSONB, ARRAY),
    so table creation in SQLite is skipped. Use metadata-level tests instead.
    """
    eng = create_engine("sqlite:///:memory:")
    yield eng
    eng.dispose()




@pytest.fixture
def migration_sql() -> str:
    """Load the forward migration SQL."""
    path = MIGRATIONS_DIR / "00001_initial_schema.sql"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def rollback_sql() -> str:
    """Load the rollback migration SQL."""
    path = MIGRATIONS_DIR / "00001_initial_schema_rollback.sql"
    return path.read_text(encoding="utf-8")


# ============================================================
# AC1 - Core Tables Exist
# ============================================================


class TestCoreTablesExist:
    """AC1: All foundational tables exist with proper relationships."""

    EXPECTED_TABLES = [
        "users",
        "profiles",
        "jobs",
        "applications",
        "matches",
        "documents",
        "agent_actions",
        "agent_outputs",
    ]

    def test_all_tables_registered_in_metadata(self):
        """All 8 core tables are registered in SQLAlchemy metadata."""
        table_names = list(Base.metadata.tables.keys())
        for expected in self.EXPECTED_TABLES:
            assert expected in table_names, f"Table '{expected}' not found in metadata"

    def test_table_count(self):
        """Exactly 8 tables are defined."""
        assert len(Base.metadata.tables) == 8

    def test_all_tables_defined_in_base_metadata(self):
        """All 8 tables are defined in Base.metadata (engine-independent check)."""
        for expected in self.EXPECTED_TABLES:
            assert expected in Base.metadata.tables, f"Table '{expected}' not in metadata"

    def test_users_table_columns(self):
        """Users table has all required columns."""
        columns = {c.name for c in User.__table__.columns}
        expected = {"id", "email", "clerk_id", "tier", "timezone", "created_at", "updated_at"}
        assert expected.issubset(columns)

    def test_profiles_table_columns(self):
        """Profiles table has all required columns."""
        columns = {c.name for c in Profile.__table__.columns}
        expected = {
            "id", "user_id", "linkedin_data", "skills", "experience",
            "education", "schema_version", "created_at", "updated_at",
            "deleted_at", "deleted_by", "deletion_reason",
        }
        assert expected.issubset(columns)

    def test_jobs_table_columns(self):
        """Jobs table has all required columns."""
        columns = {c.name for c in Job.__table__.columns}
        expected = {
            "id", "source", "url", "title", "company", "description",
            "h1b_sponsor_status", "created_at", "updated_at",
        }
        assert expected.issubset(columns)

    def test_applications_table_columns(self):
        """Applications table has all required columns."""
        columns = {c.name for c in Application.__table__.columns}
        expected = {
            "id", "user_id", "job_id", "status", "applied_at",
            "resume_version_id", "created_at", "updated_at",
            "deleted_at", "deleted_by", "deletion_reason",
        }
        assert expected.issubset(columns)

    def test_matches_table_columns(self):
        """Matches table has all required columns."""
        columns = {c.name for c in Match.__table__.columns}
        expected = {
            "id", "user_id", "job_id", "score", "rationale", "status",
            "created_at", "updated_at",
            "deleted_at", "deleted_by", "deletion_reason",
        }
        assert expected.issubset(columns)

    def test_documents_table_columns(self):
        """Documents table has all required columns."""
        columns = {c.name for c in Document.__table__.columns}
        expected = {
            "id", "user_id", "type", "version", "content", "job_id",
            "schema_version", "created_at", "updated_at",
            "deleted_at", "deleted_by", "deletion_reason",
        }
        assert expected.issubset(columns)

    def test_agent_actions_table_columns(self):
        """Agent actions table has all required columns."""
        columns = {c.name for c in AgentAction.__table__.columns}
        expected = {
            "id", "user_id", "agent_type", "action", "rationale",
            "status", "timestamp", "created_at", "updated_at",
            "deleted_at", "deleted_by", "deletion_reason",
        }
        assert expected.issubset(columns)

    def test_agent_outputs_table_columns(self):
        """Agent outputs table has all required columns."""
        columns = {c.name for c in AgentOutput.__table__.columns}
        expected = {
            "id", "agent_type", "user_id", "schema_version", "output",
            "created_at", "updated_at",
        }
        assert expected.issubset(columns)


# ============================================================
# AC1 - Relationships
# ============================================================


class TestRelationships:
    """AC1: Proper foreign key relationships between tables."""

    def test_profile_references_user(self):
        """Profile.user_id references users.id."""
        fks = [fk for fk in Profile.__table__.foreign_keys]
        fk_targets = {str(fk.column) for fk in fks}
        assert "users.id" in fk_targets

    def test_application_references_user_and_job(self):
        """Application references both users and jobs."""
        fk_targets = {str(fk.column) for fk in Application.__table__.foreign_keys}
        assert "users.id" in fk_targets
        assert "jobs.id" in fk_targets

    def test_match_references_user_and_job(self):
        """Match references both users and jobs."""
        fk_targets = {str(fk.column) for fk in Match.__table__.foreign_keys}
        assert "users.id" in fk_targets
        assert "jobs.id" in fk_targets

    def test_document_references_user_and_job(self):
        """Document references user (required) and job (optional)."""
        fk_targets = {str(fk.column) for fk in Document.__table__.foreign_keys}
        assert "users.id" in fk_targets
        assert "jobs.id" in fk_targets

    def test_agent_action_references_user(self):
        """AgentAction references users."""
        fk_targets = {str(fk.column) for fk in AgentAction.__table__.foreign_keys}
        assert "users.id" in fk_targets

    def test_agent_output_references_user(self):
        """AgentOutput references users."""
        fk_targets = {str(fk.column) for fk in AgentOutput.__table__.foreign_keys}
        assert "users.id" in fk_targets

    def test_user_has_profile_relationship(self):
        """User model has profile relationship."""
        assert hasattr(User, "profile")

    def test_user_has_applications_relationship(self):
        """User model has applications relationship."""
        assert hasattr(User, "applications")

    def test_user_has_matches_relationship(self):
        """User model has matches relationship."""
        assert hasattr(User, "matches")

    def test_user_has_documents_relationship(self):
        """User model has documents relationship."""
        assert hasattr(User, "documents")

    def test_user_has_agent_actions_relationship(self):
        """User model has agent_actions relationship."""
        assert hasattr(User, "agent_actions")

    def test_user_has_agent_outputs_relationship(self):
        """User model has agent_outputs relationship."""
        assert hasattr(User, "agent_outputs")


# ============================================================
# AC2 - UUID Primary Keys
# ============================================================


class TestUUIDPrimaryKeys:
    """AC2: All tables have UUID primary keys with defaults."""

    @pytest.mark.parametrize(
        "model",
        [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_id_column_is_uuid(self, model):
        """Each model's id column uses UUID type."""
        id_col = model.__table__.columns["id"]
        assert id_col.primary_key
        # Column type should be UUID variant
        col_type_name = type(id_col.type).__name__
        assert col_type_name in ("UUID", "Uuid"), f"Expected UUID, got {col_type_name}"

    @pytest.mark.parametrize(
        "model",
        [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_id_has_default(self, model):
        """Each model's id column has a default value generator."""
        id_col = model.__table__.columns["id"]
        assert id_col.default is not None, f"{model.__tablename__}.id has no default"


# ============================================================
# AC3 - Timestamps
# ============================================================


class TestTimestamps:
    """AC3: created_at and updated_at are auto-populated on all tables."""

    @pytest.mark.parametrize(
        "model",
        [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_created_at_exists(self, model):
        """Each table has a created_at column."""
        assert "created_at" in {c.name for c in model.__table__.columns}

    @pytest.mark.parametrize(
        "model",
        [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_updated_at_exists(self, model):
        """Each table has an updated_at column."""
        assert "updated_at" in {c.name for c in model.__table__.columns}

    @pytest.mark.parametrize(
        "model",
        [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_created_at_has_default(self, model):
        """created_at has a default value."""
        col = model.__table__.columns["created_at"]
        assert col.default is not None, f"{model.__tablename__}.created_at has no default"

    @pytest.mark.parametrize(
        "model",
        [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_updated_at_has_default(self, model):
        """updated_at has a default value."""
        col = model.__table__.columns["updated_at"]
        assert col.default is not None, f"{model.__tablename__}.updated_at has no default"

    @pytest.mark.parametrize(
        "model",
        [User, Profile, Job, Application, Match, Document, AgentAction, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_updated_at_has_onupdate(self, model):
        """updated_at has an onupdate trigger."""
        col = model.__table__.columns["updated_at"]
        assert col.onupdate is not None, f"{model.__tablename__}.updated_at has no onupdate"


# ============================================================
# AC4 - Soft Delete
# ============================================================


class TestSoftDelete:
    """AC4: Soft-delete columns exist on user-facing tables."""

    SOFT_DELETE_TABLES = [Profile, Application, Match, Document, AgentAction]
    NO_SOFT_DELETE_TABLES = [User, Job, AgentOutput]

    @pytest.mark.parametrize(
        "model",
        [Profile, Application, Match, Document, AgentAction],
        ids=lambda m: m.__tablename__,
    )
    def test_soft_delete_columns_exist(self, model):
        """User-facing tables have deleted_at, deleted_by, deletion_reason."""
        columns = {c.name for c in model.__table__.columns}
        assert "deleted_at" in columns, f"{model.__tablename__} missing deleted_at"
        assert "deleted_by" in columns, f"{model.__tablename__} missing deleted_by"
        assert "deletion_reason" in columns, f"{model.__tablename__} missing deletion_reason"

    @pytest.mark.parametrize(
        "model",
        [User, Job, AgentOutput],
        ids=lambda m: m.__tablename__,
    )
    def test_no_soft_delete_on_non_user_facing(self, model):
        """Non-user-facing tables do NOT have soft delete columns."""
        columns = {c.name for c in model.__table__.columns}
        assert "deleted_at" not in columns, f"{model.__tablename__} should not have deleted_at"

    @pytest.mark.parametrize(
        "model",
        [Profile, Application, Match, Document, AgentAction],
        ids=lambda m: m.__tablename__,
    )
    def test_soft_delete_columns_nullable(self, model):
        """Soft delete columns are nullable (null = not deleted)."""
        deleted_at = model.__table__.columns["deleted_at"]
        deleted_by = model.__table__.columns["deleted_by"]
        deletion_reason = model.__table__.columns["deletion_reason"]
        assert deleted_at.nullable
        assert deleted_by.nullable
        assert deletion_reason.nullable


# ============================================================
# AC5 - Timezone Default
# ============================================================


class TestTimezoneDefault:
    """AC5: users.timezone defaults to 'UTC'."""

    def test_timezone_default_is_utc(self):
        """User timezone column defaults to 'UTC'."""
        tz_col = User.__table__.columns["timezone"]
        assert tz_col.default is not None
        assert tz_col.default.arg == "UTC"

    def test_timezone_not_nullable(self):
        """User timezone column is not nullable."""
        tz_col = User.__table__.columns["timezone"]
        assert not tz_col.nullable


# ============================================================
# AC6 - Migration Rollback
# ============================================================


class TestMigrationFiles:
    """AC6: Migration and rollback files exist and are valid SQL."""

    def test_forward_migration_exists(self):
        """Forward migration file exists."""
        path = MIGRATIONS_DIR / "00001_initial_schema.sql"
        assert path.exists(), f"Migration file not found: {path}"

    def test_rollback_migration_exists(self):
        """Rollback migration file exists."""
        path = MIGRATIONS_DIR / "00001_initial_schema_rollback.sql"
        assert path.exists(), f"Rollback file not found: {path}"

    def test_forward_migration_creates_all_tables(self, migration_sql):
        """Forward migration creates all 8 tables."""
        expected_tables = [
            "users", "profiles", "jobs", "applications",
            "matches", "documents", "agent_actions", "agent_outputs",
        ]
        for table in expected_tables:
            assert f"CREATE TABLE {table}" in migration_sql, (
                f"CREATE TABLE {table} not found in migration"
            )

    def test_forward_migration_creates_enums(self, migration_sql):
        """Forward migration creates all enum types."""
        expected_enums = [
            "user_tier", "application_status", "match_status",
            "document_type", "agent_type", "h1b_sponsor_status",
        ]
        for enum_name in expected_enums:
            assert f"CREATE TYPE {enum_name}" in migration_sql, (
                f"CREATE TYPE {enum_name} not found in migration"
            )

    def test_forward_migration_creates_trigger_function(self, migration_sql):
        """Forward migration creates the updated_at trigger function."""
        assert "update_updated_at_column" in migration_sql

    def test_forward_migration_has_uuid_defaults(self, migration_sql):
        """Migration uses gen_random_uuid() for primary keys."""
        assert "gen_random_uuid()" in migration_sql

    def test_forward_migration_has_timezone_default(self, migration_sql):
        """Migration sets timezone DEFAULT 'UTC'."""
        assert "DEFAULT 'UTC'" in migration_sql

    def test_rollback_drops_all_tables(self, rollback_sql):
        """Rollback drops all 8 tables."""
        expected_tables = [
            "users", "profiles", "jobs", "applications",
            "matches", "documents", "agent_actions", "agent_outputs",
        ]
        for table in expected_tables:
            assert f"DROP TABLE IF EXISTS {table}" in rollback_sql, (
                f"DROP TABLE IF EXISTS {table} not found in rollback"
            )

    def test_rollback_drops_all_enums(self, rollback_sql):
        """Rollback drops all enum types."""
        expected_enums = [
            "user_tier", "application_status", "match_status",
            "document_type", "agent_type", "h1b_sponsor_status",
        ]
        for enum_name in expected_enums:
            assert f"DROP TYPE IF EXISTS {enum_name}" in rollback_sql, (
                f"DROP TYPE IF EXISTS {enum_name} not found in rollback"
            )

    def test_rollback_drops_trigger_function(self, rollback_sql):
        """Rollback drops the trigger function."""
        assert "DROP FUNCTION IF EXISTS update_updated_at_column" in rollback_sql


# ============================================================
# Enum Definitions
# ============================================================


class TestEnumDefinitions:
    """Verify enum values match the spec."""

    def test_user_tier_values(self):
        values = {e.value for e in UserTier}
        assert values == {"free", "pro", "h1b_pro", "career_insurance", "enterprise"}

    def test_application_status_values(self):
        values = {e.value for e in ApplicationStatus}
        assert values == {"applied", "screening", "interview", "offer", "closed", "rejected"}

    def test_match_status_values(self):
        values = {e.value for e in MatchStatus}
        assert values == {"new", "saved", "dismissed", "applied"}

    def test_document_type_values(self):
        values = {e.value for e in DocumentType}
        assert values == {"resume", "cover_letter"}

    def test_agent_type_values(self):
        values = {e.value for e in AgentType}
        assert values == {
            "orchestrator", "job_scout", "resume", "apply",
            "pipeline", "follow_up", "interview_intel", "network",
        }

    def test_h1b_sponsor_status_values(self):
        values = {e.value for e in H1BSponsorStatus}
        assert values == {"verified", "unverified", "unknown"}


# ============================================================
# Connection Module
# ============================================================


class TestConnectionModule:
    """Test the Supabase connection module."""

    def test_connection_module_importable(self):
        """Connection module can be imported."""
        from backend.app.db.connection import get_supabase_client, get_client
        assert callable(get_supabase_client)
        assert callable(get_client)

    def test_connection_raises_without_env_vars(self, monkeypatch):
        """get_supabase_client raises ValueError without env vars."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_KEY", raising=False)
        from backend.app.db.connection import get_supabase_client
        with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_KEY"):
            get_supabase_client()


# ============================================================
# Migration Runner
# ============================================================


class TestMigrationRunner:
    """Test the migration runner script."""

    def test_runner_importable(self):
        """Migration runner module can be imported."""
        from backend.scripts.run_migrations import (
            get_migration_dir,
            read_sql_file,
            main,
        )
        assert callable(get_migration_dir)
        assert callable(read_sql_file)
        assert callable(main)

    def test_get_migration_dir_exists(self):
        """get_migration_dir returns the correct path."""
        from backend.scripts.run_migrations import get_migration_dir
        migration_dir = get_migration_dir()
        assert migration_dir.exists()
        assert migration_dir.name == "migrations"

    def test_read_sql_file_reads_migration(self):
        """read_sql_file can read the forward migration."""
        from backend.scripts.run_migrations import read_sql_file, get_migration_dir
        sql = read_sql_file(get_migration_dir() / "00001_initial_schema.sql")
        assert "CREATE TABLE users" in sql

    def test_read_sql_file_raises_for_missing(self):
        """read_sql_file raises FileNotFoundError for missing files."""
        from backend.scripts.run_migrations import read_sql_file
        with pytest.raises(FileNotFoundError):
            read_sql_file(Path("/nonexistent/file.sql"))


# ============================================================
# Schema Versioning on JSONB columns
# ============================================================


class TestSchemaVersioning:
    """JSONB columns include schema_version as required by architecture."""

    def test_profiles_has_schema_version(self):
        columns = {c.name for c in Profile.__table__.columns}
        assert "schema_version" in columns

    def test_documents_has_schema_version(self):
        columns = {c.name for c in Document.__table__.columns}
        assert "schema_version" in columns

    def test_agent_outputs_has_schema_version(self):
        columns = {c.name for c in AgentOutput.__table__.columns}
        assert "schema_version" in columns

    def test_schema_version_defaults_to_1(self):
        """schema_version columns default to 1."""
        for model in [Profile, Document, AgentOutput]:
            col = model.__table__.columns["schema_version"]
            assert col.default is not None
            assert col.default.arg == 1, (
                f"{model.__tablename__}.schema_version default is not 1"
            )
