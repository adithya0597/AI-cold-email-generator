"""
Briefing pipeline for JobPilot.

Generates, schedules, delivers, and caches daily briefings for users.
Includes lite-briefing fallback when full generation fails.
"""

from app.agents.briefing.generator import generate_full_briefing
from app.agents.briefing.fallback import (
    generate_briefing_with_fallback,
    generate_lite_briefing,
)

__all__ = [
    "generate_full_briefing",
    "generate_briefing_with_fallback",
    "generate_lite_briefing",
]
