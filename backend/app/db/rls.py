"""
Row-Level Security context helper for SQLAlchemy sessions.

Sets the PostgreSQL session variable `app.current_user_id` via SET LOCAL,
which scopes the value to the current transaction. RLS policies reference
this variable to enforce per-user data isolation at the database level.

Usage:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_rls_context(session, user_id)
            # All queries in this transaction are now RLS-scoped
"""

import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Strict UUID v4 pattern (with hyphens)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


async def set_rls_context(session: AsyncSession, user_id: str) -> None:
    """Set the current user ID for RLS policies via SET LOCAL.

    The SET LOCAL statement scopes the setting to the current transaction,
    so it is automatically cleared when the transaction commits or rolls back.

    Args:
        session: An active SQLAlchemy async session (must be within a transaction).
        user_id: The user's UUID as a string. Validated before use.

    Raises:
        ValueError: If user_id is not a valid UUID string.
    """
    # Validate user_id is a legitimate UUID to prevent SQL injection.
    # SET LOCAL does not support bind parameters in all drivers,
    # so we validate rigorously before string formatting.
    if not isinstance(user_id, str) or not _UUID_PATTERN.match(user_id):
        raise ValueError(f"Invalid user_id: must be a valid UUID string, got {user_id!r}")

    # Double-check by parsing with stdlib UUID
    UUID(user_id)

    await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
