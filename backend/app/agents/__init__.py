"""
Agent framework for JobPilot.

Provides the BaseAgent class, AgentOutput dataclass, tier enforcement decorator,
and emergency brake module. Every agent in the system inherits from BaseAgent
and follows the run() -> execute() -> record -> publish lifecycle.

Architecture decision: Custom orchestrator (ADR-1), no LangGraph dependency.
"""

from app.agents.base import AgentOutput, BaseAgent, BrakeActive, TierViolation

__all__ = [
    "AgentOutput",
    "BaseAgent",
    "BrakeActive",
    "TierViolation",
]
