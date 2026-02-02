"""Audit logging helper for enterprise admin actions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


async def log_audit_event(
    session: AsyncSession,
    org_id: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    changes: dict | None = None,
) -> None:
    """Create an AuditLog record within the caller's transaction.

    The caller is responsible for committing the session. This function
    only adds the record to the session (no flush or commit).

    Args:
        session: Active async database session.
        org_id: Organization UUID (string).
        actor_id: User UUID of the admin performing the action.
        action: Action name (e.g. "invite_employee", "update_autonomy").
        resource_type: Type of resource affected (e.g. "organization_member").
        resource_id: Optional UUID of the specific resource.
        changes: Optional dict of changes (stored as JSONB).
    """
    entry = AuditLog(
        org_id=UUID(org_id) if isinstance(org_id, str) else org_id,
        actor_id=UUID(actor_id) if isinstance(actor_id, str) else actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=UUID(resource_id) if isinstance(resource_id, str) and resource_id else resource_id,
        changes=changes or {},
    )
    session.add(entry)
