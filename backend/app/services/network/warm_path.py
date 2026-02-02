"""
Warm Path Finder Service — discovers connections who can introduce users
to target companies.

Analyzes connection data to find 1st-degree, 2nd-degree, and alumni paths,
scores path strength, and generates suggested actions.

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
class WarmPath:
    """A single warm path to a target company via a connection."""

    contact_name: str = ""
    company: str = ""
    path_type: str = "2nd_degree"  # "1st_degree", "2nd_degree", "alumni"
    strength: str = "medium"  # "strong", "medium", "weak"
    relationship_context: str = ""
    suggested_action: str = ""
    mutual_connections: list[str] = field(default_factory=list)
    data_quality: str = "complete"  # "complete", "partial", "stub"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "contact_name": self.contact_name,
            "company": self.company,
            "path_type": self.path_type,
            "strength": self.strength,
            "relationship_context": self.relationship_context,
            "suggested_action": self.suggested_action,
            "mutual_connections": self.mutual_connections,
            "data_quality": self.data_quality,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class WarmPathService:
    """Discovers warm paths to target companies via user connections.

    Uses LLM synthesis to reason about connection data and identify
    potential introduction paths. Connection data is simulated (real
    LinkedIn API integration is deferred).
    """

    async def analyze(
        self,
        target_companies: list[str],
        connection_data: dict[str, Any],
    ) -> list[WarmPath]:
        """Analyze warm paths for target companies.

        Args:
            target_companies: Companies to find paths to.
            connection_data: User's imported connection info.

        Returns:
            List of WarmPath objects for all target companies.
        """
        if not target_companies:
            return []

        logger.info(
            "Analyzing warm paths for %d companies", len(target_companies)
        )

        async def _analyze_one(company: str) -> list[WarmPath]:
            try:
                return await self._analyze_company(company, connection_data)
            except Exception as exc:
                logger.warning(
                    "Warm path analysis failed for %s: %s", company, exc
                )
                return [
                    WarmPath(
                        contact_name=f"Connection at {company}",
                        company=company,
                        path_type="2nd_degree",
                        strength="weak",
                        relationship_context="Unable to analyze — limited data",
                        suggested_action=f"Research connections at {company} manually",
                        data_quality="partial",
                    )
                ]

        results = await asyncio.gather(
            *[_analyze_one(company) for company in target_companies]
        )
        # Flatten list of lists
        paths: list[WarmPath] = []
        for company_paths in results:
            paths.extend(company_paths)
        return paths

    async def _analyze_company(
        self,
        company: str,
        connection_data: dict[str, Any],
    ) -> list[WarmPath]:
        """Analyze warm paths for a single company using LLM."""
        from app.core.llm_clients import LLMClient

        client = LLMClient()

        contacts = connection_data.get("contacts") or []
        contact_context = ""
        if contacts:
            for c in contacts[:20]:
                if isinstance(c, dict):
                    contact_context += (
                        f"- {c.get('name', 'Unknown')} at "
                        f"{c.get('company', 'Unknown')}\n"
                    )
        else:
            contact_context = "No connection data available."

        prompt = (
            f"You are a professional networking analyst.\n"
            f"Target company: {company}\n\n"
            f"User's connections:\n{contact_context}\n\n"
            f"Identify warm paths to {company}. For each path provide a JSON "
            f"object with these keys:\n"
            f"- contact_name: string (name of the connection)\n"
            f"- path_type: string (1st_degree, 2nd_degree, or alumni)\n"
            f"- strength: string (strong, medium, or weak)\n"
            f"- relationship_context: string (how they're connected)\n"
            f"- suggested_action: string (what user should do)\n"
            f"- mutual_connections: array of strings (shared connections)\n\n"
            f"Return a JSON object with key 'paths' containing an array of "
            f"path objects. Return 1-3 paths."
        )

        data = await client.generate_json(prompt, temperature=0.4, max_tokens=1500)

        if not data or not data.get("paths"):
            return [
                WarmPath(
                    contact_name=f"Connection at {company}",
                    company=company,
                    path_type="2nd_degree",
                    strength="weak",
                    relationship_context="No specific paths identified",
                    suggested_action=f"Research your network for connections at {company}",
                    data_quality="partial",
                )
            ]

        paths: list[WarmPath] = []
        for item in data["paths"][:3]:
            if isinstance(item, dict):
                path = WarmPath(
                    contact_name=str(item.get("contact_name", "")),
                    company=company,
                    path_type=str(item.get("path_type", "2nd_degree")),
                    strength=self._score_path_strength(item),
                    relationship_context=str(
                        item.get("relationship_context", "")
                    ),
                    suggested_action=self._generate_suggested_action(
                        item, company
                    ),
                    mutual_connections=[
                        str(mc)
                        for mc in (item.get("mutual_connections") or [])
                    ],
                    data_quality="complete",
                )
                paths.append(path)

        return paths if paths else [
            WarmPath(
                contact_name=f"Connection at {company}",
                company=company,
                data_quality="partial",
            )
        ]

    def _score_path_strength(self, path_data: dict[str, Any]) -> str:
        """Score path strength based on relationship indicators.

        Considers path type, mutual connections, and relationship context.
        """
        path_type = str(path_data.get("path_type", ""))
        mutuals = path_data.get("mutual_connections") or []
        context = str(path_data.get("relationship_context", ""))

        score = 0

        # Path type scoring
        if path_type == "1st_degree":
            score += 3
        elif path_type == "alumni":
            score += 2
        elif path_type == "2nd_degree":
            score += 1

        # Mutual connections
        if len(mutuals) >= 3:
            score += 2
        elif len(mutuals) >= 1:
            score += 1

        # Relationship depth indicators
        depth_indicators = ["worked together", "collaborated", "close", "frequent"]
        if any(ind in context.lower() for ind in depth_indicators):
            score += 1

        if score >= 5:
            return "strong"
        elif score >= 3:
            return "medium"
        return "weak"

    def _generate_suggested_action(
        self, path_data: dict[str, Any], company: str
    ) -> str:
        """Generate an actionable suggestion for the warm path."""
        contact = str(path_data.get("contact_name", "your connection"))
        path_type = str(path_data.get("path_type", "2nd_degree"))

        if path_type == "1st_degree":
            return (
                f"Reach out directly to {contact} at {company} — "
                f"you're already connected"
            )
        elif path_type == "alumni":
            return (
                f"Mention shared alma mater when reaching out to "
                f"{contact} at {company}"
            )
        else:
            return (
                f"Ask your mutual connection for an intro to "
                f"{contact} at {company}"
            )
