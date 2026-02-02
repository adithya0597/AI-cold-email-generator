"""
Content Engagement Tracking Service — surfaces engagement opportunities
with target contacts' content and tracks engagement history.

Generates plausible engagement suggestions based on contact profiles
using LLM. Real LinkedIn content feed integration is deferred.

Architecture: Follows the research service pattern (like company_research.py).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EngagementOpportunity:
    """A single engagement opportunity with a target contact."""

    contact_name: str = ""
    content_topic: str = ""
    content_type: str = "post"  # "post", "article", "comment"
    suggested_comment: str = ""
    opportunity_reason: str = ""
    relevance_score: float = 0.0
    data_quality: str = "complete"  # "complete", "partial", "stub"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "contact_name": self.contact_name,
            "content_topic": self.content_topic,
            "content_type": self.content_type,
            "suggested_comment": self.suggested_comment,
            "opportunity_reason": self.opportunity_reason,
            "relevance_score": self.relevance_score,
            "data_quality": self.data_quality,
        }


@dataclass
class EngagementRecord:
    """A record of a user's engagement with a contact's content."""

    contact_name: str = ""
    engagement_type: str = ""  # "comment", "like", "share", "conversation"
    content_reference: str = ""
    timestamp: str = ""
    temperature_impact: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "contact_name": self.contact_name,
            "engagement_type": self.engagement_type,
            "content_reference": self.content_reference,
            "timestamp": self.timestamp,
            "temperature_impact": self.temperature_impact,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EngagementTrackingService:
    """Tracks engagement with target contacts' content.

    Surfaces engagement opportunities via LLM and records engagement
    history for relationship temperature scoring.
    """

    async def find_opportunities(
        self,
        contacts: list[dict[str, Any]],
        user_profile: dict[str, Any],
    ) -> list[EngagementOpportunity]:
        """Find engagement opportunities for target contacts.

        Args:
            contacts: List of contact dicts to find opportunities for.
            user_profile: User profile for relevance matching.

        Returns:
            List of EngagementOpportunity objects.
        """
        if not contacts:
            return []

        logger.info(
            "Finding engagement opportunities for %d contacts",
            len(contacts),
        )

        async def _find_one(
            contact: dict[str, Any],
        ) -> list[EngagementOpportunity]:
            try:
                return await self._analyze_contact(contact, user_profile)
            except Exception as exc:
                logger.warning(
                    "Engagement analysis failed for %s: %s",
                    contact.get("name", "unknown")[:50],
                    exc,
                )
                return [
                    EngagementOpportunity(
                        contact_name=str(contact.get("name", "Unknown")),
                        content_topic="General professional content",
                        content_type="post",
                        suggested_comment="Great insights! Thanks for sharing.",
                        opportunity_reason="Stay visible in their network",
                        relevance_score=0.3,
                        data_quality="partial",
                    )
                ]

        results = await asyncio.gather(
            *[_find_one(c) for c in contacts]
        )
        opportunities: list[EngagementOpportunity] = []
        for contact_opps in results:
            opportunities.extend(contact_opps)
        return opportunities

    async def _analyze_contact(
        self,
        contact: dict[str, Any],
        user_profile: dict[str, Any],
    ) -> list[EngagementOpportunity]:
        """Analyze a single contact for engagement opportunities."""
        from app.core.llm_clients import LLMClient

        client = LLMClient()

        contact_name = contact.get("name", "Unknown")
        contact_company = contact.get("company", "Unknown")
        contact_role = contact.get("role", "Professional")

        skills = user_profile.get("skills") or []
        skills_str = ", ".join(skills[:5]) if skills else "general professional topics"

        prompt = (
            f"You are a networking strategy advisor.\n\n"
            f"Contact: {contact_name}, {contact_role} at {contact_company}\n"
            f"User's skills/interests: {skills_str}\n\n"
            f"Suggest 1-2 content engagement opportunities. For each:\n"
            f"- content_topic: string (likely topic they'd post about)\n"
            f"- content_type: string (post, article, or comment)\n"
            f"- suggested_comment: string (thoughtful comment to leave)\n"
            f"- opportunity_reason: string (why engage with this)\n"
            f"- relevance_score: number 0.0-1.0 (relevance to user)\n\n"
            f"Return a JSON object with key 'opportunities' containing an "
            f"array of opportunity objects."
        )

        data = await client.generate_json(
            prompt, temperature=0.5, max_tokens=1000
        )

        if not data or not data.get("opportunities"):
            return [
                EngagementOpportunity(
                    contact_name=contact_name,
                    content_topic="Professional update",
                    suggested_comment="Great to see this — thanks for sharing!",
                    opportunity_reason=f"Build familiarity with {contact_name}",
                    relevance_score=0.3,
                    data_quality="partial",
                )
            ]

        opportunities: list[EngagementOpportunity] = []
        for item in data["opportunities"][:2]:
            if isinstance(item, dict):
                opportunities.append(
                    EngagementOpportunity(
                        contact_name=contact_name,
                        content_topic=str(
                            item.get("content_topic", "")
                        ),
                        content_type=str(
                            item.get("content_type", "post")
                        ),
                        suggested_comment=str(
                            item.get("suggested_comment", "")
                        ),
                        opportunity_reason=str(
                            item.get("opportunity_reason", "")
                        ),
                        relevance_score=float(
                            item.get("relevance_score", 0.5)
                        ),
                        data_quality="complete",
                    )
                )

        return opportunities if opportunities else [
            EngagementOpportunity(
                contact_name=contact_name,
                data_quality="partial",
            )
        ]

    async def record_engagement(
        self,
        user_id: str,
        record: EngagementRecord,
    ) -> None:
        """Store an engagement record in agent_outputs.

        Args:
            user_id: The user who engaged.
            record: The engagement record to store.
        """
        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentOutput as AgentOutputModel

        logger.info(
            "Recording engagement for user=%s contact=%s",
            user_id,
            record.contact_name,
        )

        async with AsyncSessionLocal() as session:
            output = AgentOutputModel(
                agent_type="network",
                user_id=user_id,
                output={
                    "type": "engagement_record",
                    "record": record.to_dict(),
                },
                schema_version=1,
            )
            session.add(output)
            await session.commit()

    async def get_engagement_history(
        self,
        user_id: str,
        contact_name: str,
    ) -> list[EngagementRecord]:
        """Retrieve engagement history for a specific contact.

        Args:
            user_id: The user to query.
            contact_name: The contact to filter by.

        Returns:
            List of EngagementRecord objects.
        """
        from sqlalchemy import select

        from app.db.engine import AsyncSessionLocal
        from app.db.models import AgentOutput as AgentOutputModel

        records: list[EngagementRecord] = []

        async with AsyncSessionLocal() as session:
            stmt = (
                select(AgentOutputModel)
                .where(AgentOutputModel.agent_type == "network")
                .where(AgentOutputModel.user_id == user_id)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        for row in rows:
            output = row.output or {}
            if output.get("type") == "engagement_record":
                rec = output.get("record", {})
                if rec.get("contact_name") == contact_name:
                    records.append(
                        EngagementRecord(
                            contact_name=rec.get("contact_name", ""),
                            engagement_type=rec.get("engagement_type", ""),
                            content_reference=rec.get(
                                "content_reference", ""
                            ),
                            timestamp=rec.get("timestamp", ""),
                            temperature_impact=float(
                                rec.get("temperature_impact", 0.0)
                            ),
                        )
                    )

        return records
