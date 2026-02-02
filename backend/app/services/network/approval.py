"""
Network Approval Service — manages human approval for direct outreach.

All direct messages require user approval. This service creates
ApprovalQueueItem entries, manages pending outreach, and processes
approve/edit/reject decisions.

Uses the existing approval_queue table and ApprovalQueueItem model.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class NetworkApprovalService:
    """Manages the approval workflow for network outreach messages.

    Hard constraint: Agent NEVER sends messages without approval
    regardless of autonomy level.
    """

    async def queue_outreach(
        self,
        user_id: str,
        draft: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Create an approval queue item for an outreach draft.

        Args:
            user_id: The user requesting outreach.
            draft: The message draft dict.
            context: Relationship context (temperature, path type, etc.).

        Returns:
            The ID of the created ApprovalQueueItem (as string).
        """
        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=48)

        item_id = uuid.uuid4()

        async with AsyncSessionLocal() as session:
            item = ApprovalQueueItem(
                id=item_id,
                user_id=user_id,
                agent_type="network",
                action_name="outreach_request",
                payload={
                    "draft": draft,
                    "context": context,
                },
                status="pending",
                rationale="Network outreach requires human approval",
                confidence=0.0,
                expires_at=expires_at,
            )
            session.add(item)
            await session.commit()

        logger.info(
            "Queued outreach for approval: user=%s item=%s",
            user_id,
            str(item_id),
        )

        # Publish approval event via Redis
        try:
            from app.cache.redis_client import get_redis_client

            redis = await get_redis_client()
            await redis.publish(
                f"agent:status:{user_id}",
                json.dumps(
                    {
                        "type": "approval.new",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": now.isoformat(),
                        "user_id": user_id,
                        "agent_type": "network",
                        "title": "New outreach draft requires your approval",
                        "severity": "action_required",
                        "data": {
                            "action_name": "outreach_request",
                            "recipient": draft.get("recipient_name", ""),
                        },
                    }
                ),
            )
        except Exception as exc:
            logger.warning("Failed to publish approval event: %s", exc)

        return str(item_id)

    async def get_pending_outreach(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch pending network outreach approvals for a user.

        Args:
            user_id: The user to query.

        Returns:
            List of dicts with approval item details.
        """
        from sqlalchemy import select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ApprovalQueueItem)
                .where(ApprovalQueueItem.user_id == user_id)
                .where(ApprovalQueueItem.agent_type == "network")
                .where(ApprovalQueueItem.status == "pending")
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

        return [
            {
                "id": str(item.id),
                "agent_type": item.agent_type,
                "action_name": item.action_name,
                "payload": item.payload,
                "status": item.status,
                "rationale": item.rationale,
                "expires_at": (
                    item.expires_at.isoformat() if item.expires_at else None
                ),
            }
            for item in items
        ]

    async def process_approval(
        self,
        item_id: str,
        action: str,
        edited_message: str | None = None,
    ) -> dict[str, Any]:
        """Process an approval decision.

        Args:
            item_id: The ApprovalQueueItem ID.
            action: "approve", "edit_approve", or "reject".
            edited_message: Updated message text (for edit_approve).

        Returns:
            Dict with processing result.
        """
        from sqlalchemy import select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import ApprovalQueueItem

        now = datetime.now(timezone.utc)

        try:
            parsed_id = uuid.UUID(item_id)
        except (ValueError, AttributeError):
            return {"status": "error", "message": f"Invalid item ID: {item_id}"}

        async with AsyncSessionLocal() as session:
            stmt = select(ApprovalQueueItem).where(
                ApprovalQueueItem.id == parsed_id
            )
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()

            if item is None:
                return {"status": "error", "message": "Item not found"}

            if action == "approve":
                item.status = "approved"
                item.decided_at = now
            elif action == "edit_approve":
                item.status = "approved"
                item.decided_at = now
                if edited_message and item.payload:
                    payload = dict(item.payload)
                    draft = payload.get("draft", {})
                    draft["message"] = edited_message
                    payload["draft"] = draft
                    item.payload = payload
            elif action == "reject":
                item.status = "rejected"
                item.decided_at = now
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                }

            await session.commit()

        logger.info(
            "Processed approval: item=%s action=%s", item_id, action
        )

        return {
            "status": "success",
            "item_id": item_id,
            "action": action,
            "decided_at": now.isoformat(),
        }
