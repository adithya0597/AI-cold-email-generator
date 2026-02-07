"""
Migration runner for Supabase SQL migrations.

Supports forward migration (apply) and rollback (revert).
Uses the Supabase client to execute raw SQL migrations.

Usage:
    python -m backend.scripts.run_migrations apply
    python -m backend.scripts.run_migrations rollback
"""

import os
import sys
from pathlib import Path


def get_migration_dir() -> Path:
    """Get the migrations directory path."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "supabase" / "migrations"


def read_sql_file(filepath: Path) -> str:
    """Read and return contents of a SQL file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Migration file not found: {filepath}")
    return filepath.read_text(encoding="utf-8")


def apply_migration() -> bool:
    """Apply the forward migration."""
    from backend.app.db.connection import get_supabase_client

    migration_dir = get_migration_dir()
    sql_file = migration_dir / "00001_initial_schema.sql"

    print(f"Applying migration: {sql_file.name}")
    sql = read_sql_file(sql_file)

    client = get_supabase_client()
    try:
        client.postgrest.session.headers.update(
            {"Content-Type": "application/json"}
        )
        # Execute via Supabase RPC or direct SQL
        result = client.rpc("exec_sql", {"query": sql}).execute()
        print(f"Migration applied successfully: {sql_file.name}")
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False


def rollback_migration() -> bool:
    """Rollback the migration using the rollback script."""
    from backend.app.db.connection import get_supabase_client

    migration_dir = get_migration_dir()
    sql_file = migration_dir / "00001_initial_schema_rollback.sql"

    print(f"Rolling back migration: {sql_file.name}")
    sql = read_sql_file(sql_file)

    client = get_supabase_client()
    try:
        result = client.rpc("exec_sql", {"query": sql}).execute()
        print(f"Rollback successful: {sql_file.name}")
        return True
    except Exception as e:
        print(f"Rollback failed: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scripts.run_migrations [apply|rollback]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "apply":
        success = apply_migration()
    elif command == "rollback":
        success = rollback_migration()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python -m backend.scripts.run_migrations [apply|rollback]")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
