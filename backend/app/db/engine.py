"""
SQLAlchemy async engine and session factory for JobPilot.

This is the PRIMARY database access layer for all application data.
Uses asyncpg driver with Supabase-compatible settings.

For Supabase SDK (storage/auth only), see supabase_client.py.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Use Supabase direct connection (port 5432), NOT PgBouncer (port 6543).
# - statement_cache_size=0: Prevents asyncpg DuplicatePreparedStatementError
#   when used behind PgBouncer or Supabase connection pooler.
# - server_settings jit=off: Avoids JIT compilation overhead on short queries,
#   which can cause timeouts on Supabase's shared infrastructure.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "statement_cache_size": 0,
        "server_settings": {"jit": "off"},
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
