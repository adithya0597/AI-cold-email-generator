"""
Interview Intel Agent — generates interview prep briefings.

Detects interviews (via pipeline status or manual trigger), orchestrates
research sub-steps (company, interviewer, questions, STAR), assembles a
structured prep briefing, and schedules delivery 24 hours before the interview.

Research sub-steps are stubs in this story; real implementations come in
stories 8-2 through 8-5.

Architecture: Extends BaseAgent (ADR-1 custom orchestrator).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.base import AgentOutput, BaseAgent

logger = logging.getLogger(__name__)


class InterviewIntelAgent(BaseAgent):
    """Interview Intel agent that generates prep briefings.

    Class attribute ``agent_type`` is used by BaseAgent for recording
    outputs, activities, and publishing WebSocket events.
    """

    agent_type = "interview_intel"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Execute the interview intel workflow.

        Expected task_data keys:
            - application_id (str, required): The application being interviewed for.
            - company_name (str, optional): Company name for research.
            - interviewer_names (list[str], optional): Names of interviewers.
            - interview_datetime (str ISO, optional): When the interview is scheduled.
            - role_title (str, optional): The role being interviewed for.
            - seniority (str, optional): Seniority level of the role.

        Returns:
            AgentOutput with the assembled prep briefing in data.
        """
        application_id = task_data.get("application_id")
        if not application_id:
            return AgentOutput(
                action="interview_prep_failed",
                rationale="No application_id provided in task_data",
                confidence=1.0,
                data={"error": "missing_application_id"},
            )

        company_name = task_data.get("company_name", "Unknown Company")
        interviewer_names = task_data.get("interviewer_names") or []
        interview_datetime_str = task_data.get("interview_datetime")
        role_title = task_data.get("role_title", "Software Engineer")
        seniority = task_data.get("seniority", "mid")

        # Load user profile for STAR suggestions
        profile = await self._load_user_profile(user_id)

        # Step 1: Company research
        company_research = await self._run_company_research(company_name)

        # Step 2: Interviewer research (skip if no names)
        interviewer_research = []
        if interviewer_names:
            interviewer_research = await self._run_interviewer_research(
                interviewer_names
            )

        # Step 3: Question generation
        questions = await self._generate_questions(
            role_title, company_name, seniority
        )

        # Step 4: STAR response suggestions
        star_suggestions = await self._generate_star_suggestions(
            questions, profile
        )

        # Step 5: Assemble briefing
        briefing = self._assemble_briefing(
            company_research=company_research,
            interviewer_research=interviewer_research,
            questions=questions,
            star_suggestions=star_suggestions,
            application_id=application_id,
            company_name=company_name,
            role_title=role_title,
        )

        # Step 6: Schedule delivery if interview_datetime is known
        delivery_info = {}
        if interview_datetime_str:
            delivery_info = await self._schedule_delivery(
                user_id=user_id,
                interview_datetime_str=interview_datetime_str,
                briefing=briefing,
            )

        # Compute confidence based on data completeness
        confidence = self._compute_confidence(
            company_research, interviewer_research, questions, star_suggestions
        )

        return AgentOutput(
            action="interview_prep_complete",
            rationale=(
                f"Prep briefing generated for {company_name} — "
                f"{role_title} interview"
            ),
            confidence=confidence,
            data={
                "briefing": briefing,
                "delivery": delivery_info,
                "application_id": application_id,
            },
        )

    # ------------------------------------------------------------------
    # User profile loader
    # ------------------------------------------------------------------

    async def _load_user_profile(self, user_id: str) -> dict[str, Any]:
        """Load user profile data for STAR suggestion generation."""
        from app.agents.orchestrator import get_user_context

        context = await get_user_context(user_id)
        return context.get("profile") or {}

    # ------------------------------------------------------------------
    # Research sub-steps (stubs — real implementations in 8-2 to 8-5)
    # ------------------------------------------------------------------

    async def _run_company_research(self, company_name: str) -> dict[str, Any]:
        """Run company research via CompanyResearchService."""
        from app.services.research.company_research import CompanyResearchService

        logger.info("Running company research for %s", company_name)
        service = CompanyResearchService()
        result = await service.research(company_name)
        return result.to_dict()

    async def _run_interviewer_research(
        self, names: list[str]
    ) -> list[dict[str, Any]]:
        """Run interviewer research via InterviewerResearchService."""
        from app.services.research.interviewer_research import (
            InterviewerResearchService,
        )

        logger.info("Running interviewer research for %s", names)
        service = InterviewerResearchService()
        profiles = await service.research(names)
        return [p.to_dict() for p in profiles]

    async def _generate_questions(
        self, role_title: str, company_name: str, seniority: str
    ) -> dict[str, list[str]]:
        """Generate interview questions via QuestionGenerationService."""
        from app.services.research.question_generation import (
            QuestionGenerationService,
        )

        logger.info(
            "Generating questions for %s at %s (%s)",
            role_title, company_name, seniority,
        )
        service = QuestionGenerationService()
        result = await service.generate(role_title, company_name, seniority)
        return result.to_dict()

    async def _generate_star_suggestions(
        self,
        questions: dict[str, list[str]],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate STAR response suggestions via StarSuggestionService."""
        from app.services.research.star_suggestions import StarSuggestionService

        behavioral = questions.get("behavioral") or []
        logger.info("Generating STAR suggestions for %d questions", len(behavioral))
        service = StarSuggestionService()
        results = await service.generate(questions, profile)
        return [r.to_dict() for r in results]

    # ------------------------------------------------------------------
    # Briefing assembly
    # ------------------------------------------------------------------

    def _assemble_briefing(
        self,
        company_research: dict[str, Any],
        interviewer_research: list[dict[str, Any]],
        questions: dict[str, list[str]],
        star_suggestions: list[dict[str, Any]],
        application_id: str,
        company_name: str,
        role_title: str,
    ) -> dict[str, Any]:
        """Merge all research sub-step outputs into a single briefing dict."""
        total_questions = sum(len(v) for v in questions.values())
        return {
            "application_id": application_id,
            "company_name": company_name,
            "role_title": role_title,
            "company_research": company_research,
            "interviewer_research": interviewer_research,
            "questions": questions,
            "star_suggestions": star_suggestions,
            "summary": {
                "total_questions": total_questions,
                "interviewers_researched": len(interviewer_research),
                "has_company_research": bool(company_research.get("mission")),
                "has_star_suggestions": len(star_suggestions) > 0,
            },
        }

    # ------------------------------------------------------------------
    # Delivery scheduling
    # ------------------------------------------------------------------

    async def _schedule_delivery(
        self,
        user_id: str,
        interview_datetime_str: str,
        briefing: dict[str, Any],
    ) -> dict[str, Any]:
        """Schedule briefing delivery 24h before interview (or immediately)."""
        from datetime import timedelta

        from app.worker.celery_app import celery_app

        try:
            interview_dt = datetime.fromisoformat(interview_datetime_str)
        except (ValueError, TypeError):
            logger.warning(
                "Invalid interview_datetime: %s", interview_datetime_str
            )
            return {"scheduled": False, "reason": "invalid_datetime"}

        # Ensure timezone-aware
        if interview_dt.tzinfo is None:
            interview_dt = interview_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delivery_time = interview_dt - timedelta(hours=24)

        # Clamp to now if < 24h away
        if delivery_time < now:
            delivery_time = now

        task_result = celery_app.send_task(
            "app.worker.tasks.briefing_generate",
            args=[user_id],
            kwargs={"channels": ["in_app", "email"]},
            eta=delivery_time,
        )

        return {
            "scheduled": True,
            "delivery_time": delivery_time.isoformat(),
            "celery_task_id": task_result.id,
        }

    # ------------------------------------------------------------------
    # Confidence computation
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        company_research: dict[str, Any],
        interviewer_research: list[dict[str, Any]],
        questions: dict[str, list[str]],
        star_suggestions: list[dict[str, Any]],
    ) -> float:
        """Compute confidence score based on data completeness (0.0 to 1.0)."""
        score = 0.0
        total = 4.0

        # Company research has content
        if company_research.get("mission"):
            score += 1.0

        # Interviewer research present (or none expected)
        if interviewer_research:
            score += 1.0
        else:
            # No interviewers to research is not a confidence penalty
            total -= 1.0

        # Questions generated
        total_questions = sum(len(v) for v in questions.values())
        if total_questions > 0:
            score += 1.0

        # STAR suggestions generated
        if star_suggestions:
            score += 1.0

        return round(score / total, 2) if total > 0 else 0.5
