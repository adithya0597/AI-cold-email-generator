"""
Introduction Request Message Drafts Service — generates personalized
introduction request messages for warm paths.

Each draft includes personalized opening, clear ask, context, and an
easy-out. Messages are 3-5 sentences. Drafts require human approval
before any action is taken.

Architecture: Follows the research service pattern (like star_suggestions.py).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class IntroDraft:
    """A single introduction request message draft."""

    recipient_name: str = ""
    connection_name: str = ""
    target_company: str = ""
    message: str = ""
    tone: str = "professional"  # "professional", "casual", "formal"
    word_count: int = 0
    data_quality: str = "complete"  # "complete", "partial", "stub"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "recipient_name": self.recipient_name,
            "connection_name": self.connection_name,
            "target_company": self.target_company,
            "message": self.message,
            "tone": self.tone,
            "word_count": self.word_count,
            "data_quality": self.data_quality,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class IntroDraftService:
    """Generates introduction request message drafts for warm paths.

    Uses LLM to create personalized, 3-5 sentence messages with
    personalized opening, clear ask, context, and easy-out.
    """

    async def generate(
        self,
        warm_paths: list[dict[str, Any]],
        user_profile: dict[str, Any],
    ) -> list[IntroDraft]:
        """Generate intro drafts for warm paths.

        Args:
            warm_paths: List of warm path dicts (from WarmPathService).
            user_profile: User profile data for personalization.

        Returns:
            List of IntroDraft objects.
        """
        if not warm_paths:
            return []

        logger.info(
            "Generating intro drafts for %d warm paths", len(warm_paths)
        )

        async def _generate_one(path: dict[str, Any]) -> IntroDraft:
            try:
                return await self._generate_for_path(path, user_profile)
            except Exception as exc:
                logger.warning(
                    "Intro draft generation failed for %s: %s",
                    path.get("contact_name", "unknown")[:50],
                    exc,
                )
                return self._get_fallback(path)

        drafts = await asyncio.gather(
            *[_generate_one(p) for p in warm_paths]
        )
        return list(drafts)

    async def _generate_for_path(
        self,
        path: dict[str, Any],
        user_profile: dict[str, Any],
    ) -> IntroDraft:
        """Generate a single intro draft using LLM."""
        from app.core.llm_clients import LLMClient

        client = LLMClient()
        prompt = self._build_prompt(path, user_profile)

        data = await client.generate_json(
            prompt, temperature=0.6, max_tokens=800
        )

        if not data or not data.get("message"):
            return self._get_fallback(path)

        message = str(data.get("message", ""))

        return IntroDraft(
            recipient_name=str(
                path.get("contact_name", "")
            ),
            connection_name=str(
                data.get("connection_name", path.get("contact_name", "Your connection"))
            ),
            target_company=str(path.get("company", "")),
            message=message,
            tone=str(data.get("tone", "professional")),
            word_count=len(message.split()),
            data_quality="complete",
        )

    def _build_prompt(
        self,
        path: dict[str, Any],
        profile: dict[str, Any],
    ) -> str:
        """Construct LLM prompt for intro draft generation."""
        contact = path.get("contact_name", "the contact")
        company = path.get("company", "the company")
        path_type = path.get("path_type", "2nd_degree")
        context = path.get("relationship_context", "")

        skills = profile.get("skills") or []
        skills_str = ", ".join(skills[:5]) if skills else "various skills"

        return (
            f"You are a professional networking coach.\n\n"
            f"Write an introduction request message with these requirements:\n"
            f"- Recipient: {contact} at {company}\n"
            f"- Connection type: {path_type}\n"
            f"- Relationship context: {context}\n"
            f"- User skills: {skills_str}\n\n"
            f"Message requirements:\n"
            f"- 3-5 sentences ONLY\n"
            f"- Personalized opening referencing the relationship\n"
            f"- Clear, specific ask about {company}\n"
            f"- Context on why interested in the company\n"
            f"- End with an easy out like 'No worries if not possible'\n\n"
            f"Return a JSON object with keys:\n"
            f"- message: string (the full message text)\n"
            f"- tone: string (professional, casual, or formal)"
        )

    def _get_fallback(self, path: dict[str, Any]) -> IntroDraft:
        """Return a generic template when LLM fails."""
        contact = path.get("contact_name", "there")
        company = path.get("company", "your company")
        message = (
            f"Hi {contact}! I noticed we're connected through our "
            f"professional network. I'm very interested in opportunities "
            f"at {company} and would love to learn more about the team "
            f"and culture. Would you be open to a quick chat? "
            f"No worries if not possible."
        )
        return IntroDraft(
            recipient_name=str(path.get("contact_name", "")),
            connection_name=str(
                path.get("contact_name", "Your connection")
            ),
            target_company=str(path.get("company", "")),
            message=message,
            tone="professional",
            word_count=len(message.split()),
            data_quality="partial",
        )
