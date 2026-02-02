"""
Interviewer Research Service — researches interviewer backgrounds from public data.

Gathers publicly available information about interview panelists and synthesizes
it into structured profiles with conversation starters for rapport building.

Privacy: Only public data sources are used (public LinkedIn, articles, talks).
No private or scraped data is collected.

Architecture: Follows the research service pattern (like company_research.py).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class InterviewerProfile:
    """Structured output from interviewer research."""

    name: str = ""
    current_role: str = ""
    tenure: str = ""
    career_highlights: list[str] = field(default_factory=list)
    public_content: list[dict[str, str]] = field(default_factory=list)
    speaking_topics: list[str] = field(default_factory=list)
    shared_interests: list[str] = field(default_factory=list)
    conversation_starters: list[dict[str, str]] = field(default_factory=list)
    data_quality: str = "complete"  # "complete", "partial", "stub"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "current_role": self.current_role,
            "tenure": self.tenure,
            "career_highlights": self.career_highlights,
            "public_content": self.public_content,
            "speaking_topics": self.speaking_topics,
            "shared_interests": self.shared_interests,
            "conversation_starters": self.conversation_starters,
            "data_quality": self.data_quality,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class InterviewerResearchService:
    """Researches interviewer backgrounds from public data.

    Uses LLM synthesis to generate structured interviewer profiles
    from publicly available information only.
    """

    async def research(self, names: list[str]) -> list[InterviewerProfile]:
        """Research multiple interviewers and return structured profiles.

        Args:
            names: List of interviewer names to research.

        Returns:
            List of InterviewerProfile, one per name (order preserved).
        """
        logger.info("Starting interviewer research for %d names", len(names))

        async def _research_one(name: str) -> InterviewerProfile:
            try:
                profile = await self._synthesize_interviewer(name)
                starters = self._generate_conversation_starters(profile)
                profile.conversation_starters = starters
                return profile
            except Exception as exc:
                logger.warning(
                    "Interviewer research failed for %s: %s", name, exc
                )
                return InterviewerProfile(
                    name=name,
                    current_role="Unknown (research unavailable)",
                    data_quality="partial",
                )

        profiles = await asyncio.gather(*[_research_one(n) for n in names])

        logger.info(
            "Interviewer research complete: %d/%d profiles",
            len(profiles), len(names),
        )
        return list(profiles)

    # ------------------------------------------------------------------
    # LLM synthesis
    # ------------------------------------------------------------------

    async def _synthesize_interviewer(self, name: str) -> InterviewerProfile:
        """Synthesize interviewer profile from LLM using public data only."""
        from app.core.llm_clients import LLMClient

        client = LLMClient()

        prompt = (
            f"You are a research analyst preparing interview prep data.\n"
            f"Research target: {name}\n\n"
            f"Using ONLY publicly available information, provide a JSON object "
            f"with these exact keys:\n"
            f"- current_role: string (current job title and company)\n"
            f"- tenure: string (how long in current role, e.g. '3 years')\n"
            f"- career_highlights: array of strings (notable career milestones)\n"
            f"- public_content: array of objects with keys: type, title, url "
            f"(public articles, talks, LinkedIn posts)\n"
            f"- speaking_topics: array of strings (topics they speak/write about)\n"
            f"- shared_interests: array of strings (common professional interests)\n\n"
            f"IMPORTANT: Only include publicly available information. "
            f"Do not fabricate or infer private details.\n"
            f"Return 2-4 items per array field."
        )

        data = await client.generate_json(prompt, temperature=0.3, max_tokens=1500)

        if not data:
            return InterviewerProfile(
                name=name,
                current_role="Unknown (LLM returned empty response)",
                data_quality="partial",
            )

        # Parse public content items ensuring correct structure
        content_items: list[dict[str, str]] = []
        for item in (data.get("public_content") or []):
            if isinstance(item, dict):
                content_items.append({
                    "type": str(item.get("type", "")),
                    "title": str(item.get("title", "")),
                    "url": str(item.get("url", "")),
                })

        return InterviewerProfile(
            name=name,
            current_role=str(data.get("current_role", "")),
            tenure=str(data.get("tenure", "")),
            career_highlights=[
                str(h) for h in (data.get("career_highlights") or [])
            ],
            public_content=content_items,
            speaking_topics=[
                str(t) for t in (data.get("speaking_topics") or [])
            ],
            shared_interests=[
                str(i) for i in (data.get("shared_interests") or [])
            ],
            data_quality="complete",
        )

    # ------------------------------------------------------------------
    # Conversation starters
    # ------------------------------------------------------------------

    def _generate_conversation_starters(
        self, profile: InterviewerProfile
    ) -> list[dict[str, str]]:
        """Generate conversation starters based on common ground."""
        starters: list[dict[str, str]] = []

        # Starter from speaking topics
        for topic in profile.speaking_topics[:2]:
            starters.append({
                "topic": topic,
                "opener": f"I noticed your work on {topic} — I'd love to hear more about your perspective.",
                "source": "speaking_topics",
            })

        # Starter from public content
        for content in profile.public_content[:1]:
            if content.get("title"):
                starters.append({
                    "topic": content["title"],
                    "opener": f"I read your piece on '{content['title']}' — it resonated with my experience.",
                    "source": "public_content",
                })

        # Starter from career highlights
        if profile.career_highlights:
            starters.append({
                "topic": "Career Journey",
                "opener": f"Your experience with {profile.career_highlights[0]} is impressive — what drew you to that path?",
                "source": "career_highlights",
            })

        return starters
