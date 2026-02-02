"""
Question Generation Service — generates tailored interview questions.

Produces 10-15 likely interview questions categorized into behavioral,
technical, company-specific, and role-specific, tailored to seniority level.

Architecture: Follows the research service pattern (like company_research.py).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class GeneratedQuestions:
    """Structured output from question generation."""

    behavioral: list[str] = field(default_factory=list)
    technical: list[str] = field(default_factory=list)
    company_specific: list[str] = field(default_factory=list)
    role_specific: list[str] = field(default_factory=list)
    seniority: str = ""
    data_quality: str = "complete"  # "complete", "partial", "fallback"

    @property
    def total_count(self) -> int:
        return (
            len(self.behavioral)
            + len(self.technical)
            + len(self.company_specific)
            + len(self.role_specific)
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the dict format expected by the agent."""
        return {
            "behavioral": self.behavioral,
            "technical": self.technical,
            "company_specific": self.company_specific,
            "role_specific": self.role_specific,
            "seniority": self.seniority,
            "data_quality": self.data_quality,
        }


# ---------------------------------------------------------------------------
# Fallback questions by seniority
# ---------------------------------------------------------------------------

_FALLBACK_QUESTIONS: dict[str, dict[str, list[str]]] = {
    "junior": {
        "behavioral": [
            "Tell me about a time you learned a new technology quickly.",
            "Describe a project you completed as part of a team.",
            "How do you handle receiving critical feedback?",
        ],
        "technical": [
            "Walk me through your approach to debugging an issue.",
            "What data structures would you use for this problem?",
            "Explain a recent technical concept you learned.",
        ],
        "company_specific": [
            "Why do you want to work at {company}?",
            "What excites you about {company}'s products?",
        ],
        "role_specific": [
            "How would you approach your first 30 days in this role?",
            "What skills are you most eager to develop?",
        ],
    },
    "mid": {
        "behavioral": [
            "Tell me about a time you led a project under tight deadlines.",
            "Describe a situation where you had to resolve a team conflict.",
            "Give an example of when you mentored a junior colleague.",
        ],
        "technical": [
            "How would you design a system to handle high traffic?",
            "Describe your approach to code review.",
            "What are the trade-offs between SQL and NoSQL for this use case?",
        ],
        "company_specific": [
            "Why do you want to work at {company}?",
            "How would you improve {company}'s current product?",
        ],
        "role_specific": [
            "How would you approach your first 90 days as a {role}?",
            "Describe your ideal development workflow.",
        ],
    },
    "senior": {
        "behavioral": [
            "Tell me about a time you influenced technical direction without authority.",
            "Describe a situation where you had to make a difficult trade-off.",
            "How do you balance technical debt with feature delivery?",
            "Give an example of cross-team collaboration you drove.",
        ],
        "technical": [
            "How would you architect a distributed system for this problem?",
            "Describe your approach to system reliability and observability.",
            "How do you evaluate build-vs-buy decisions?",
        ],
        "company_specific": [
            "Why do you want to work at {company}?",
            "What technical challenges do you think {company} faces?",
            "How would you approach scaling {company}'s engineering org?",
        ],
        "role_specific": [
            "How would you approach your first 90 days as a senior {role}?",
            "How do you set technical standards for a team?",
            "Describe your approach to mentoring and knowledge sharing.",
        ],
    },
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class QuestionGenerationService:
    """Generates tailored interview questions for a specific role.

    Uses LLM to generate questions tailored to role, company, and
    seniority level. Falls back to template questions on failure.
    """

    async def generate(
        self,
        role_title: str,
        company_name: str,
        seniority: str = "mid",
    ) -> GeneratedQuestions:
        """Generate interview questions for a role.

        Args:
            role_title: Job title being interviewed for.
            company_name: Company name for company-specific questions.
            seniority: Seniority level (junior, mid, senior).

        Returns:
            GeneratedQuestions with categorized questions.
        """
        logger.info(
            "Generating questions for %s at %s (%s)",
            role_title, company_name, seniority,
        )

        normalized_seniority = self._normalize_seniority(seniority)

        try:
            result = await self._generate_with_llm(
                role_title, company_name, normalized_seniority
            )
            if result.total_count >= 10:
                return result
            # If LLM didn't generate enough, fall through to fallback
            logger.warning(
                "LLM generated only %d questions, using fallback",
                result.total_count,
            )
        except Exception as exc:
            logger.warning("LLM question generation failed: %s", exc)

        return self._get_fallback_questions(
            role_title, company_name, normalized_seniority
        )

    def _normalize_seniority(self, seniority: str) -> str:
        """Normalize seniority string to junior/mid/senior."""
        lower = seniority.lower().strip()
        if lower in ("junior", "entry", "associate", "intern"):
            return "junior"
        if lower in ("senior", "staff", "principal", "lead", "director"):
            return "senior"
        return "mid"

    async def _generate_with_llm(
        self,
        role_title: str,
        company_name: str,
        seniority: str,
    ) -> GeneratedQuestions:
        """Generate questions using LLM."""
        from app.core.llm_clients import LLMClient

        client = LLMClient()

        prompt = (
            f"You are an interview preparation expert.\n"
            f"Generate 10-15 likely interview questions for:\n"
            f"- Role: {role_title}\n"
            f"- Company: {company_name}\n"
            f"- Seniority: {seniority}\n\n"
            f"Return a JSON object with these exact keys:\n"
            f"- behavioral: array of 3-4 behavioral interview questions\n"
            f"- technical: array of 3-4 technical questions specific to the role\n"
            f"- company_specific: array of 2-3 questions about the company\n"
            f"- role_specific: array of 2-3 questions about day-to-day role expectations\n\n"
            f"Tailor question difficulty and scope to {seniority} level.\n"
            f"Questions should be realistic and commonly asked."
        )

        data = await client.generate_json(prompt, temperature=0.4, max_tokens=1500)

        if not data:
            raise ValueError("LLM returned empty response")

        return GeneratedQuestions(
            behavioral=[str(q) for q in (data.get("behavioral") or [])],
            technical=[str(q) for q in (data.get("technical") or [])],
            company_specific=[str(q) for q in (data.get("company_specific") or [])],
            role_specific=[str(q) for q in (data.get("role_specific") or [])],
            seniority=seniority,
            data_quality="complete",
        )

    def _get_fallback_questions(
        self,
        role_title: str,
        company_name: str,
        seniority: str,
    ) -> GeneratedQuestions:
        """Return template-based fallback questions."""
        templates = _FALLBACK_QUESTIONS.get(seniority, _FALLBACK_QUESTIONS["mid"])

        def fill(qs: list[str]) -> list[str]:
            return [
                q.format(company=company_name, role=role_title) for q in qs
            ]

        return GeneratedQuestions(
            behavioral=fill(templates["behavioral"]),
            technical=fill(templates["technical"]),
            company_specific=fill(templates["company_specific"]),
            role_specific=fill(templates["role_specific"]),
            seniority=seniority,
            data_quality="fallback",
        )
