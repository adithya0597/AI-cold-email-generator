"""
ADR-1 Prototype: Custom Agent Orchestration (plain Python)

This is a PROTOTYPE file for evaluating LangGraph vs Custom orchestrator.
It is NOT imported by production code. Prefixed with underscore to indicate
prototype status.

Demonstrates:
- BaseAgent class with run() -> execute() -> record_output() flow
- Brake check via Redis flag (simulated)
- requires_tier() decorator for tier enforcement
- L2 approval queue via DB table (simulated)
- AgentOutput dataclass as standard output format

Zero framework dependencies -- plain Python, asyncio, dataclasses.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Agent output dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentOutput:
    """Standard output every agent must produce."""
    action: str
    rationale: str
    confidence: float = 0.0
    alternatives_considered: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    requires_approval: bool = False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BrakeActive(Exception):
    """Raised when emergency brake is active for a user."""
    pass


class TierViolation(Exception):
    """Raised when action requires a higher autonomy tier."""
    pass


# ---------------------------------------------------------------------------
# Simulated infrastructure (no real Redis/DB in prototype)
# ---------------------------------------------------------------------------

_BRAKED_USERS: set[str] = set()
_USER_TIERS: dict[str, str] = {}  # user_id -> tier
_APPROVAL_QUEUE: list[dict] = []  # Simulated DB table


async def check_brake(user_id: str) -> bool:
    """Check if emergency brake is active for user.

    Production: Redis EXISTS paused:{user_id}
    Prototype: In-memory set lookup
    """
    return user_id in _BRAKED_USERS


async def check_brake_or_raise(user_id: str) -> None:
    """Check brake and raise BrakeActive if active.

    Convenience for calling between agent steps (before each LLM call,
    DB write, or external API call).
    """
    if await check_brake(user_id):
        raise BrakeActive(f"Emergency brake active for {user_id}")


async def _get_user_tier(user_id: str) -> str:
    """Get user's autonomy level.

    Production: SELECT autonomy_level FROM user_preferences WHERE user_id = ...
    Prototype: In-memory dict lookup
    """
    return _USER_TIERS.get(user_id, "l0")


# ---------------------------------------------------------------------------
# Tier enforcement decorator
# ---------------------------------------------------------------------------

TIER_ORDER = {"l0": 0, "l1": 1, "l2": 2, "l3": 3}


def requires_tier(min_tier: str, action_type: str = "read"):
    """Decorator enforcing autonomy tier before agent action.

    Behavior by tier:
    - L0: Suggestion only. Read actions run but output tagged "suggest:".
          Write actions always raise TierViolation.
    - L1: Read actions execute. Write actions raise TierViolation.
    - L2: Read actions execute directly. Write actions queue for approval.
    - L3: All actions execute directly.

    Always checks brake FIRST (safety critical).
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self: "BaseAgent", user_id: str, *args, **kwargs):
            # 1. Always check brake first (safety critical)
            await check_brake_or_raise(user_id)

            # 2. Get user tier
            user_tier = await _get_user_tier(user_id)
            user_level = TIER_ORDER.get(user_tier, 0)
            required_level = TIER_ORDER.get(min_tier, 0)

            # 3. Enforce tier
            if user_level < required_level:
                raise TierViolation(
                    f"Action requires {min_tier}, user has {user_tier}"
                )

            # 4. L0: suggestion only
            if user_tier == "l0":
                if action_type == "write":
                    raise TierViolation("L0 users cannot perform write actions")
                # Run the function but tag output as suggestion
                output = await func(self, user_id, *args, **kwargs)
                output.action = f"suggest:{output.action}"
                return output

            # 5. L1: can read, cannot write
            if user_tier == "l1" and action_type == "write":
                raise TierViolation("L1 users cannot perform write actions")

            # 6. L2 + write: queue for approval
            if user_tier == "l2" and action_type == "write":
                return await self._queue_for_approval(
                    user_id, func.__name__, args, kwargs
                )

            # 7. L2 read or L3: execute directly
            return await func(self, user_id, *args, **kwargs)

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

class BaseAgent:
    """Base class for all JobPilot agents.

    Provides:
    - run(): Entry point with brake check, execute, record, publish
    - execute(): Abstract method subclasses override
    - _record_output(): Persist to agent_outputs table (stubbed)
    - _publish_event(): Redis pub/sub for WebSocket (stubbed)
    - _queue_for_approval(): L2 approval queue insertion (stubbed)
    """

    agent_type: str = "base"

    async def run(self, user_id: str, task_data: dict) -> AgentOutput:
        """Main entry point. Checks brake, executes, records, publishes."""
        # Check brake before any work
        if await check_brake(user_id):
            raise BrakeActive(f"Emergency brake active for {user_id}")

        # Execute agent logic (subclass implements)
        output = await self.execute(user_id, task_data)

        # Record output to DB
        await self._record_output(user_id, output)

        # Publish real-time event via Redis pub/sub
        await self._publish_event(user_id, output)

        return output

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Override in subclass with actual agent logic."""
        raise NotImplementedError("Subclasses must implement execute()")

    async def _record_output(self, user_id: str, output: AgentOutput) -> None:
        """Persist agent output to database.

        Production: INSERT INTO agent_outputs (user_id, agent_type, output, ...)
        Prototype: Print to stdout
        """
        print(f"  [RECORD] user={user_id} agent={self.agent_type} "
              f"action={output.action} rationale={output.rationale}")

    async def _publish_event(self, user_id: str, output: AgentOutput) -> None:
        """Publish real-time event via Redis pub/sub for WebSocket.

        Production: redis.publish(f"agent:status:{user_id}", json.dumps(event))
        Prototype: Print to stdout
        """
        print(f"  [EVENT] agent.{self.agent_type}.completed -> user={user_id}")

    async def _queue_for_approval(
        self,
        user_id: str,
        action_name: str,
        args: tuple,
        kwargs: dict,
    ) -> AgentOutput:
        """Store pending action in approval queue.

        Production: INSERT INTO approval_queue (user_id, agent_type, action_name, payload, status, expires_at)
        Prototype: Append to in-memory list
        """
        item = {
            "user_id": user_id,
            "agent_type": self.agent_type,
            "action_name": action_name,
            "payload": {"args": list(args), "kwargs": kwargs},
            "status": "pending",
        }
        _APPROVAL_QUEUE.append(item)
        print(f"  [APPROVAL] Queued {action_name} for user={user_id} "
              f"(queue size: {len(_APPROVAL_QUEUE)})")

        return AgentOutput(
            action="queued_for_approval",
            rationale=f"{action_name} requires L2 approval",
            confidence=1.0,
            requires_approval=True,
        )

    async def _record_activity(
        self,
        user_id: str,
        event_type: str,
        title: str,
        severity: str = "info",
        data: dict | None = None,
    ) -> None:
        """Record activity for feed display.

        Production: INSERT INTO agent_activities (user_id, event_type, title, severity, data)
        Prototype: Print to stdout
        """
        print(f"  [ACTIVITY] {event_type}: {title} (severity={severity})")


# ---------------------------------------------------------------------------
# Prototype agent implementation
# ---------------------------------------------------------------------------

class PrototypeAgent(BaseAgent):
    """Dummy agent for prototype evaluation."""

    agent_type: str = "prototype"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Dummy execution -- returns canned output."""
        return AgentOutput(
            action=f"executed:{task_data.get('task_type', 'unknown')}",
            rationale="Task executed successfully (prototype)",
            confidence=0.85,
            alternatives_considered=["approach_a", "approach_b"],
            data={"input": task_data},
        )

    @requires_tier(min_tier="l0", action_type="read")
    async def search(self, user_id: str, query: str) -> AgentOutput:
        """Search action (read) -- available to all tiers."""
        return AgentOutput(
            action="search_completed",
            rationale=f"Found results for: {query}",
            confidence=0.9,
            data={"query": query, "results_count": 5},
        )

    @requires_tier(min_tier="l1", action_type="write")
    async def apply_to_job(self, user_id: str, job_id: str) -> AgentOutput:
        """Apply action (write) -- L2 queues for approval, L3 executes."""
        return AgentOutput(
            action="applied",
            rationale=f"Applied to job {job_id}",
            confidence=0.8,
            data={"job_id": job_id},
        )


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

async def _run_scenarios() -> None:
    """Run all 4 prototype scenarios."""
    agent = PrototypeAgent()

    # Scenario 1: L0 user -- should produce suggestion only
    print("\n=== Scenario 1: L0 User (suggestion only) ===")
    _USER_TIERS["user_l0"] = "l0"
    result = await agent.search("user_l0", query="python developer")
    assert result.action.startswith("suggest:"), \
        f"L0 should produce suggestion, got: {result.action}"
    print(f"  PASS: L0 user received suggestion-only output: {result.action}")

    # Scenario 2: L2 user with write action -- should queue for approval
    print("\n=== Scenario 2: L2 User Write (approval queue) ===")
    _USER_TIERS["user_l2"] = "l2"
    result = await agent.apply_to_job("user_l2", job_id="job_123")
    assert result.action == "queued_for_approval", \
        f"L2 write should queue for approval, got: {result.action}"
    assert result.requires_approval is True
    assert len(_APPROVAL_QUEUE) == 1
    print(f"  PASS: L2 write action queued for approval")
    print(f"  Queue item: {json.dumps(_APPROVAL_QUEUE[-1], indent=2)}")

    # Scenario 3: L3 user -- should execute directly
    print("\n=== Scenario 3: L3 User (direct execution) ===")
    _USER_TIERS["user_l3"] = "l3"
    result = await agent.apply_to_job("user_l3", job_id="job_456")
    assert result.action == "applied", \
        f"L3 should execute directly, got: {result.action}"
    print(f"  PASS: L3 user action executed directly: {result.action}")

    # Scenario 4: Braked user -- should raise BrakeActive
    print("\n=== Scenario 4: Braked User (emergency brake) ===")
    _BRAKED_USERS.add("user_braked")
    _USER_TIERS["user_braked"] = "l3"
    try:
        result = await agent.run("user_braked", {"task_type": "search"})
        print("  FAIL: Should have raised BrakeActive")
    except BrakeActive as e:
        print(f"  PASS: BrakeActive raised: {e}")
    finally:
        _BRAKED_USERS.discard("user_braked")

    # Bonus: Verify brake check happens BEFORE tier check
    print("\n=== Scenario 5: Brake Check Order (brake before tier) ===")
    _BRAKED_USERS.add("user_order_test")
    _USER_TIERS["user_order_test"] = "l3"
    try:
        # Even though user is L3 (highest tier), brake should block
        result = await agent.search("user_order_test", query="test")
        print("  FAIL: Should have raised BrakeActive")
    except BrakeActive:
        print("  PASS: Brake checked before tier (BrakeActive raised for L3 user)")
    finally:
        _BRAKED_USERS.discard("user_order_test")

    print("\n=== Custom Prototype Complete ===")
    print("Observations:")
    print("  - Plain Python: dataclass, decorator, async class -- no framework to learn")
    print("  - Brake check in decorator runs BEFORE tier check (correct safety order)")
    print("  - Tier enforcement is explicit and readable in decorator")
    print("  - Approval queue is a simple DB insert + WebSocket notification")
    print("  - No automatic checkpointing -- Celery acks_late handles crash recovery")
    print("  - Zero additional dependencies beyond what's already installed")
    print(f"  - Total approval queue items: {len(_APPROVAL_QUEUE)}")


def run_scenarios() -> None:
    """Synchronous entry point for __main__ execution."""
    asyncio.run(_run_scenarios())


if __name__ == "__main__":
    run_scenarios()
