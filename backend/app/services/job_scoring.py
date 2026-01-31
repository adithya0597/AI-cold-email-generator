"""
LLM-enhanced job scoring service.

Provides a two-stage scoring pipeline: jobs that pass the heuristic pre-filter
are refined by GPT-3.5-turbo for a nuanced 0-100 score with rationale and
per-dimension breakdown.

Architecture: Standalone module called from JobScoutAgent.execute().
Heavy dependencies (OpenAIClient, cost_tracker) are lazy-imported inside the
scoring function to avoid import-time side effects.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """Result of LLM or heuristic job scoring."""

    score: int  # 0-100 final score
    rationale: str  # Human-readable explanation
    breakdown: dict[str, int]  # Per-dimension scores
    model_used: str  # e.g. "gpt-3.5-turbo"
    used_llm: bool  # True if LLM was used, False if heuristic fallback


SCORING_PROMPT = """Score this job match (0-100) for a candidate.

JOB:
Title: {title}
Company: {company}
Location: {location}
Salary: {salary_range}
Description (first 500 chars): {description_truncated}

CANDIDATE PREFERENCES:
Target roles: {target_titles}
Target locations: {target_locations}
Salary range: {salary_min}-{salary_target}
Seniority: {seniority_levels}
Min company size: {min_company_size}
Skills: {skills}

Score breakdown (each 0-100):
- title_match: how well job title matches target roles
- skills_overlap: how many candidate skills appear in job
- location_match: location compatibility (remote bonus)
- salary_match: salary range compatibility
- company_size: company size vs preference
- seniority_match: seniority level alignment

Respond with JSON only:
{{"score": <0-100>, "rationale": "<1-2 sentences>", "breakdown": {{"title_match": <n>, "skills_overlap": <n>, "location_match": <n>, "salary_match": <n>, "company_size": <n>, "seniority_match": <n>}}}}"""


def _build_prompt(job: Any, preferences: dict, profile: dict) -> str:
    """Build the scoring prompt from job data and user context."""
    description = (getattr(job, "description", "") or "")[:500]
    salary_min = getattr(job, "salary_min", None)
    salary_max = getattr(job, "salary_max", None)
    if salary_min is not None and salary_max is not None:
        salary_range = f"${salary_min:,}-${salary_max:,}"
    elif salary_min is not None:
        salary_range = f"${salary_min:,}+"
    elif salary_max is not None:
        salary_range = f"Up to ${salary_max:,}"
    else:
        salary_range = "Not specified"

    return SCORING_PROMPT.format(
        title=getattr(job, "title", "") or "Unknown",
        company=getattr(job, "company", "") or "Unknown",
        location=getattr(job, "location", "") or "Unknown",
        salary_range=salary_range,
        description_truncated=description,
        target_titles=", ".join(preferences.get("target_titles") or []),
        target_locations=", ".join(preferences.get("target_locations") or []),
        salary_min=preferences.get("salary_minimum") or "Any",
        salary_target=preferences.get("salary_target") or "Any",
        seniority_levels=", ".join(preferences.get("seniority_levels") or []),
        min_company_size=preferences.get("min_company_size") or "Any",
        skills=", ".join((profile.get("skills") or [])),
    )


def _parse_llm_response(data: dict[str, Any]) -> ScoringResult | None:
    """Parse and validate the LLM JSON response.

    Returns a ScoringResult on success or None if the response is unusable.
    """
    try:
        raw_score = data.get("score")
        if raw_score is None:
            return None

        score = int(raw_score)
        # Clamp to 0-100
        score = max(0, min(100, score))

        rationale = str(data.get("rationale", "No rationale provided"))

        raw_breakdown = data.get("breakdown") or {}
        breakdown: dict[str, int] = {}
        for key in (
            "title_match",
            "skills_overlap",
            "location_match",
            "salary_match",
            "company_size",
            "seniority_match",
        ):
            val = raw_breakdown.get(key)
            if val is not None:
                breakdown[key] = max(0, min(100, int(val)))
            else:
                breakdown[key] = 50  # neutral default

        return ScoringResult(
            score=score,
            rationale=rationale,
            breakdown=breakdown,
            model_used="",  # filled by caller
            used_llm=True,
        )
    except (ValueError, TypeError, KeyError) as exc:
        logger.warning("Failed to parse LLM scoring response: %s", exc)
        return None


async def score_job_with_llm(
    job: Any,
    preferences: dict,
    profile: dict,
    user_id: str | None = None,
    heuristic_score: int = 0,
) -> ScoringResult:
    """Score a job using GPT-3.5-turbo for refined matching.

    On any failure, returns a fallback ScoringResult using *heuristic_score*
    with ``used_llm=False``.

    Parameters
    ----------
    job:
        Job object (or SimpleNamespace) with title, company, location, etc.
    preferences:
        User preferences dict (target_titles, target_locations, ...).
    profile:
        User profile dict (skills, ...).
    user_id:
        Optional user id for cost tracking.
    heuristic_score:
        Fallback score to use when LLM fails.
    """
    # Lazy imports to avoid import-time side effects
    from app.core.llm_clients import OpenAIClient
    from app.core.llm_config import LLMConfig

    fallback = ScoringResult(
        score=heuristic_score,
        rationale="Heuristic score (LLM unavailable)",
        breakdown={},
        model_used="heuristic",
        used_llm=False,
    )

    try:
        prompt = _build_prompt(job, preferences, profile)
        model = LLMConfig.FAST_MODEL
        client = OpenAIClient()
        client.model = model  # Override default model

        data = await client.generate_json(
            prompt,
            temperature=LLMConfig.TEMPERATURE_ANALYSIS,
            max_tokens=LLMConfig.MAX_TOKENS_FAST,
        )

        result = _parse_llm_response(data)
        if result is None:
            logger.warning("LLM returned unusable response, falling back to heuristic")
            return fallback

        result.model_used = model

        # Cost tracking
        if user_id is not None:
            from app.observability.cost_tracker import track_llm_cost

            input_tokens = len(prompt) // 4
            response_text = json.dumps(data)
            output_tokens = len(response_text) // 4
            try:
                await track_llm_cost(user_id, model, input_tokens, output_tokens)
            except Exception:
                logger.exception("Cost tracking failed for user=%s", user_id)

        return result

    except Exception as exc:
        logger.warning("LLM scoring failed, using heuristic fallback: %s", exc)
        return fallback
