"""
Tier enforcement for the JobPilot agent framework.

Provides the ``@requires_tier()`` decorator and the ``AutonomyGate`` class
for enforcing autonomy levels (L0--L3) before agent actions.

Tier behavior:
    - **L0** (suggestions only): Read actions run but output is tagged
      ``suggest:``.  Write actions always raise ``TierViolation``.
    - **L1** (drafts): Read actions execute.  Write actions raise
      ``TierViolation``.
    - **L2** (supervised): Read actions execute directly.  Write actions
      are routed to the approval queue via ``BaseAgent._queue_for_approval()``.
    - **L3** (autonomous): All actions execute directly (volume caps
      are enforced by individual agents, not the tier decorator).

The brake is always checked **first** -- even L3 users are blocked when
the emergency brake is active.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# Tier ordering: higher number = more autonomy
TIER_ORDER: dict[str, int] = {"l0": 0, "l1": 1, "l2": 2, "l3": 3}


def requires_tier(min_tier: str, action_type: str = "read"):
    """Decorator enforcing autonomy tier before an agent action.

    Must be applied to an ``async`` method on a ``BaseAgent`` subclass.
    The first positional argument after ``self`` must be ``user_id: str``.

    Args:
        min_tier: Minimum tier required to attempt this action (e.g. ``"l1"``).
        action_type: ``"read"`` for queries/searches, ``"write"`` for mutations
            (apply, send, modify).
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self: "BaseAgent", user_id: str, *args, **kwargs):
            from app.agents.brake import check_brake_or_raise

            # 1. Always check brake first (safety critical)
            await check_brake_or_raise(user_id)

            # 2. Look up user's autonomy level
            user_tier = await _get_user_tier(user_id)
            user_level = TIER_ORDER.get(user_tier, 0)
            required_level = TIER_ORDER.get(min_tier, 0)

            # 3. Enforce minimum tier
            if user_level < required_level:
                from app.agents.base import TierViolation

                raise TierViolation(
                    f"Action requires {min_tier}, user has {user_tier}"
                )

            # 4. L0: suggestion only
            if user_tier == "l0":
                if action_type == "write":
                    from app.agents.base import TierViolation

                    raise TierViolation("L0 users cannot perform write actions")
                # Run the function but tag output as suggestion
                output = await func(self, user_id, *args, **kwargs)
                output.action = f"suggest:{output.action}"
                return output

            # 5. L1: can read, cannot write
            if user_tier == "l1" and action_type == "write":
                from app.agents.base import TierViolation

                raise TierViolation("L1 users cannot perform write actions")

            # 6. L2 + write: queue for approval
            if user_tier == "l2" and action_type == "write":
                return await self._queue_for_approval(
                    user_id, func.__name__, args, kwargs
                )

            # 7. L2 read or L3 any: execute directly
            return await func(self, user_id, *args, **kwargs)

        return wrapper

    return decorator


class AutonomyGate:
    """Programmatic tier check for agents that need non-decorator enforcement.

    Use this when the tier decision must be made inside agent logic rather
    than at the method boundary.

    Example::

        gate = AutonomyGate()
        decision = await gate.check(user_id, "write")
        if decision == "execute":
            ...
        elif decision == "suggest":
            ...
        elif decision == "queue_approval":
            ...
        elif decision == "blocked":
            ...
    """

    async def check(
        self, user_id: str, action_type: str = "read"
    ) -> Literal["execute", "suggest", "queue_approval", "blocked"]:
        """Determine what tier enforcement allows for this user and action.

        Args:
            user_id: The user performing the action.
            action_type: ``"read"`` or ``"write"``.

        Returns:
            One of ``"execute"``, ``"suggest"``, ``"queue_approval"``,
            or ``"blocked"``.
        """
        from app.agents.brake import check_brake

        # Brake overrides everything
        if await check_brake(user_id):
            return "blocked"

        user_tier = await _get_user_tier(user_id)

        if user_tier == "l0":
            if action_type == "write":
                return "blocked"
            return "suggest"

        if user_tier == "l1":
            if action_type == "write":
                return "blocked"
            return "execute"

        if user_tier == "l2":
            if action_type == "write":
                return "queue_approval"
            return "execute"

        # l3
        return "execute"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_user_tier(user_id: str) -> str:
    """Look up the user's autonomy level from the database.

    Returns ``"l0"`` if no preference record is found (safest default).
    """
    from sqlalchemy import select

    from app.db.engine import AsyncSessionLocal
    from app.db.models import UserPreference

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserPreference.autonomy_level).where(
                UserPreference.user_id == user_id
            )
        )
        tier = result.scalar_one_or_none()
        return tier or "l0"
