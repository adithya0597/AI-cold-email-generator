"""
SQLAlchemy async engine and session factory for JobPilot.

This is the PRIMARY database access layer for all application data.
Uses asyncpg driver with Supabase-compatible settings for PostgreSQL,
or aiosqlite for local SQLite development.

For Supabase SDK (storage/auth only), see supabase_client.py.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _create_engine():
    """Create async engine with driver-appropriate settings."""
    db_url = settings.DATABASE_URL

    # SQLite (local development)
    if db_url.startswith("sqlite"):
        return create_async_engine(
            db_url,
            echo=settings.DEBUG,
            # SQLite doesn't support pool_size or connect_args like PostgreSQL
            connect_args={"check_same_thread": False},
        )

    # PostgreSQL (production / Supabase)
    # Use Supabase direct connection (port 5432), NOT PgBouncer (port 6543).
    # - statement_cache_size=0: Prevents asyncpg DuplicatePreparedStatementError
    #   when used behind PgBouncer or Supabase connection pooler.
    # - server_settings jit=off: Avoids JIT compilation overhead on short queries,
    #   which can cause timeouts on Supabase's shared infrastructure.
    return create_async_engine(
        db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        connect_args={
            "statement_cache_size": 0,
            "server_settings": {"jit": "off"},
        },
    )


engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
