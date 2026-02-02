"""
Company Research Service — compiles company information into interview-ready insights.

Gathers public data about a company (mission, news, products, competitors,
culture indicators) and synthesizes it via LLM into a structured briefing
with conversation hooks for interview preparation.

Privacy: Only public data sources are used. No scraping of sites that
prohibit it via robots.txt or Terms of Service.

Architecture: Follows the research service pattern (like h1b_service.py).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CompanyResearchResult:
    """Structured output from company research."""

    mission: str = ""
    recent_news: list[dict[str, str]] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    culture_indicators: list[str] = field(default_factory=list)
    challenges_opportunities: list[str] = field(default_factory=list)
    conversation_hooks: list[dict[str, str]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    data_quality: str = "complete"  # "complete", "partial", "stub"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "mission": self.mission,
            "recent_news": self.recent_news,
            "products": self.products,
            "competitors": self.competitors,
            "culture_indicators": self.culture_indicators,
            "challenges_opportunities": self.challenges_opportunities,
            "conversation_hooks": self.conversation_hooks,
            "sources": self.sources,
            "data_quality": self.data_quality,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CompanyResearchService:
    """Compiles company research into interview-ready insights.

    Uses LLM synthesis to generate structured company information
    from available public data. Web search is a stub in this story;
    real search integration is deferred.
    """

    async def research(self, company_name: str) -> CompanyResearchResult:
        """Run company research and return structured result.

        Args:
            company_name: Name of the company to research.

        Returns:
            CompanyResearchResult with all available research data.
        """
        logger.info("Starting company research for %s", company_name)

        # Step 1: Search for raw data (stub)
        raw_data: list[dict[str, str]] = []
        try:
            raw_data = await self._search_web(company_name)
        except Exception as exc:
            logger.warning("Web search failed for %s: %s", company_name, exc)

        # Step 2: Synthesize with LLM
        result: CompanyResearchResult
        try:
            result = await self._synthesize_with_llm(company_name, raw_data)
        except Exception as exc:
            logger.warning("LLM synthesis failed for %s: %s", company_name, exc)
            result = CompanyResearchResult(
                mission=f"{company_name} (research unavailable)",
                data_quality="partial",
            )

        # Step 3: Generate conversation hooks
        try:
            hooks = await self._generate_conversation_hooks(result)
            result.conversation_hooks = hooks
        except Exception as exc:
            logger.warning(
                "Conversation hook generation failed for %s: %s",
                company_name, exc,
            )

        logger.info(
            "Company research complete for %s (quality=%s)",
            company_name, result.data_quality,
        )
        return result

    # ------------------------------------------------------------------
    # Web search (stub)
    # ------------------------------------------------------------------

    async def _search_web(self, company_name: str) -> list[dict[str, str]]:
        """Stub: web search for company data.

        Returns empty list. Real web search integration (e.g., Serper,
        SerpAPI) is deferred to a future story. The LLM synthesis works
        with empty search results by generating from training knowledge.
        """
        logger.info("Web search stub called for %s (returning empty)", company_name)
        return []

    # ------------------------------------------------------------------
    # LLM synthesis
    # ------------------------------------------------------------------

    async def _synthesize_with_llm(
        self, company_name: str, raw_data: list[dict[str, str]]
    ) -> CompanyResearchResult:
        """Synthesize raw search results into structured company insights."""
        from app.core.llm_clients import LLMClient

        client = LLMClient()

        context = ""
        if raw_data:
            context = "\n".join(
                f"- {item.get('title', '')}: {item.get('snippet', '')}"
                for item in raw_data
            )
        else:
            context = "No web search results available. Use your training knowledge."

        prompt = (
            f"You are a company research analyst preparing interview briefing data.\n"
            f"Research target: {company_name}\n\n"
            f"Available context:\n{context}\n\n"
            f"Provide a JSON object with these exact keys:\n"
            f"- mission: string (company mission/values statement)\n"
            f"- recent_news: array of objects with keys: title, summary, source_url, date\n"
            f"- products: array of strings (key products/services)\n"
            f"- competitors: array of strings (main competitors)\n"
            f"- culture_indicators: array of strings (culture signals)\n"
            f"- challenges_opportunities: array of strings (recent challenges or opportunities)\n"
            f"- sources: array of strings (source URLs or attributions)\n\n"
            f"Return 3-5 items per array field. Use only publicly available information."
        )

        data = await client.generate_json(prompt, temperature=0.3, max_tokens=2000)

        if not data:
            return CompanyResearchResult(
                mission=f"{company_name} (LLM returned empty response)",
                data_quality="partial",
            )

        # Parse news items ensuring correct structure
        news_items = []
        for item in (data.get("recent_news") or []):
            if isinstance(item, dict):
                news_items.append({
                    "title": str(item.get("title", "")),
                    "summary": str(item.get("summary", "")),
                    "source_url": str(item.get("source_url", "")),
                    "date": str(item.get("date", "")),
                })

        return CompanyResearchResult(
            mission=str(data.get("mission", "")),
            recent_news=news_items,
            products=[str(p) for p in (data.get("products") or [])],
            competitors=[str(c) for c in (data.get("competitors") or [])],
            culture_indicators=[str(ci) for ci in (data.get("culture_indicators") or [])],
            challenges_opportunities=[
                str(co) for co in (data.get("challenges_opportunities") or [])
            ],
            sources=[str(s) for s in (data.get("sources") or [])],
            data_quality="complete",
        )

    # ------------------------------------------------------------------
    # Conversation hooks
    # ------------------------------------------------------------------

    async def _generate_conversation_hooks(
        self, research: CompanyResearchResult
    ) -> list[dict[str, str]]:
        """Generate "Talk about this" suggestions from research data."""
        hooks: list[dict[str, str]] = []

        # Hook from mission
        if research.mission:
            hooks.append({
                "topic": "Company Mission",
                "talking_point": f"I was drawn to {research.mission[:100]}...",
                "source": "company_mission",
                "relevance": "Shows you understand and align with their values",
            })

        # Hooks from recent news
        for news in research.recent_news[:2]:
            hooks.append({
                "topic": news.get("title", "Recent Development"),
                "talking_point": news.get("summary", ""),
                "source": news.get("source_url", "news"),
                "relevance": "Demonstrates you follow the company actively",
            })

        # Hook from products
        if research.products:
            hooks.append({
                "topic": "Key Products",
                "talking_point": (
                    f"I'm particularly interested in {research.products[0]} "
                    f"and how it fits into the broader strategy"
                ),
                "source": "product_research",
                "relevance": "Shows product awareness and strategic thinking",
            })

        # Hook from challenges
        if research.challenges_opportunities:
            hooks.append({
                "topic": "Industry Challenge",
                "talking_point": research.challenges_opportunities[0],
                "source": "industry_analysis",
                "relevance": "Shows awareness of business context and industry trends",
            })

        return hooks
