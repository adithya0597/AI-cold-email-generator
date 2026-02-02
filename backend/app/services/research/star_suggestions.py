"""
STAR Suggestion Service — generates STAR-formatted response suggestions.

For each behavioral interview question, generates 2-3 STAR (Situation, Task,
Action, Result) outlines drawing from the user's profile data (skills,
experience, past roles).

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
class StarOutline:
    """A single STAR response outline."""

    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "situation": self.situation,
            "task": self.task,
            "action": self.action,
            "result": self.result,
        }


@dataclass
class StarSuggestion:
    """STAR suggestions for a single question."""

    question: str = ""
    suggestions: list[StarOutline] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "suggestions": [s.to_dict() for s in self.suggestions],
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class StarSuggestionService:
    """Generates STAR-formatted response suggestions from user profile.

    Uses LLM to create personalized STAR outlines for behavioral
    questions, drawing from the user's skills and experience.
    """

    async def generate(
        self,
        questions: dict[str, list[str]],
        profile: dict[str, Any],
    ) -> list[StarSuggestion]:
        """Generate STAR suggestions for behavioral questions.

        Args:
            questions: Dict of categorized questions (uses 'behavioral' key).
            profile: User profile dict with skills, experience, etc.

        Returns:
            List of StarSuggestion, one per behavioral question.
        """
        behavioral = questions.get("behavioral") or []
        if not behavioral:
            return []

        logger.info(
            "Generating STAR suggestions for %d behavioral questions",
            len(behavioral),
        )

        async def _generate_one(question: str) -> StarSuggestion:
            try:
                return await self._generate_for_question(question, profile)
            except Exception as exc:
                logger.warning(
                    "STAR generation failed for question: %s — %s",
                    question[:50], exc,
                )
                return self._get_fallback(question)

        suggestions = await asyncio.gather(
            *[_generate_one(q) for q in behavioral]
        )
        return list(suggestions)

    async def _generate_for_question(
        self,
        question: str,
        profile: dict[str, Any],
    ) -> StarSuggestion:
        """Generate STAR outlines for a single question using LLM."""
        from app.core.llm_clients import LLMClient

        client = LLMClient()

        # Build profile context
        skills = profile.get("skills") or []
        experience = profile.get("experience") or []
        profile_context = ""
        if skills:
            profile_context += f"Skills: {', '.join(skills[:10])}\n"
        if experience:
            for exp in experience[:3]:
                if isinstance(exp, dict):
                    profile_context += (
                        f"- {exp.get('title', 'Role')} at "
                        f"{exp.get('company', 'Company')}: "
                        f"{exp.get('description', '')}\n"
                    )
                else:
                    profile_context += f"- {exp}\n"

        if not profile_context:
            profile_context = "No profile data available. Generate generic examples."

        prompt = (
            f"You are an interview coach helping prepare STAR responses.\n\n"
            f"Question: {question}\n\n"
            f"Candidate profile:\n{profile_context}\n\n"
            f"Generate 2-3 STAR response outlines. Each should have:\n"
            f"- situation: Brief context (1-2 sentences)\n"
            f"- task: What the candidate was responsible for\n"
            f"- action: Specific steps taken (2-3 key actions)\n"
            f"- result: Quantified outcome where possible\n\n"
            f"Return a JSON object with key 'suggestions' containing an array "
            f"of objects with keys: situation, task, action, result.\n"
            f"Draw from the candidate's actual experience where possible."
        )

        data = await client.generate_json(prompt, temperature=0.5, max_tokens=1500)

        if not data or not data.get("suggestions"):
            return self._get_fallback(question)

        outlines: list[StarOutline] = []
        for item in data["suggestions"][:3]:  # Cap at 3
            if isinstance(item, dict):
                outlines.append(StarOutline(
                    situation=str(item.get("situation", "")),
                    task=str(item.get("task", "")),
                    action=str(item.get("action", "")),
                    result=str(item.get("result", "")),
                ))

        if not outlines:
            return self._get_fallback(question)

        return StarSuggestion(question=question, suggestions=outlines)

    def _get_fallback(self, question: str) -> StarSuggestion:
        """Return generic STAR template as fallback."""
        return StarSuggestion(
            question=question,
            suggestions=[
                StarOutline(
                    situation="Describe the context and background of a relevant experience",
                    task="Explain what you were specifically responsible for",
                    action="Detail the steps you took to address the situation",
                    result="Share the measurable outcome or impact of your actions",
                ),
            ],
        )
