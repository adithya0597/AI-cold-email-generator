"""
Apply Agent -- submits job applications on behalf of users.

Given a user's prepared materials (tailored resume, cover letter) and a target
job, determines the submission method, records the application in the database,
and returns the outcome.

Architecture: Extends BaseAgent (ADR-1 custom orchestrator).
CRITICAL: Respects daily application limits per user tier.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.base import AgentOutput, BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Daily application limits per tier
# ---------------------------------------------------------------------------

DAILY_APPLICATION_LIMITS: dict[str, int] = {
    "free": 5,
    "pro": 25,
    "h1b_pro": 25,
    "career_insurance": 50,
    "enterprise": 100,
}


# ---------------------------------------------------------------------------
# ApplyAgent
# ---------------------------------------------------------------------------


class ApplyAgent(BaseAgent):
    """Application submission agent.

    Class attribute ``agent_type`` identifies this agent for routing & logging.
    """

    agent_type = "apply"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Execute the application submission workflow.

        1. Validate inputs (job_id required)
        2. Load user context (profile + tier)
        3. Check daily application limit
        4. Load target job
        5. Select submission method
        6. Prepare materials (resume + cover letter)
        7. Record application in database
        8. Return AgentOutput

        Args:
            user_id: Clerk user ID.
            task_data: Must contain ``job_id`` (UUID string).

        Returns:
            AgentOutput with application details.
        """
        from app.agents.orchestrator import get_user_context

        job_id = task_data.get("job_id")
        if not job_id:
            return AgentOutput(
                action="application_failed",
                rationale="No job_id provided in task_data",
                confidence=1.0,
                data={"error": "missing_job_id"},
            )

        # 1. Load user context
        context = await get_user_context(user_id)
        profile = context.get("profile") or {}
        preferences = context.get("preferences") or {}

        if not profile.get("skills") and not profile.get("experience"):
            return AgentOutput(
                action="application_failed",
                rationale="User has no profile data",
                confidence=1.0,
                data={"error": "empty_profile"},
            )

        # 2. Check daily limit
        tier = preferences.get("tier") or "free"
        limit_result = await self._check_daily_limit(user_id, tier)
        if limit_result is not None:
            return limit_result

        # 3. Load job details
        job = await self._load_job(job_id)
        if not job:
            await self._record_failure_activity(
                user_id, "job_not_found", job_id=job_id
            )
            return AgentOutput(
                action="application_failed",
                rationale=f"Job {job_id} not found",
                confidence=1.0,
                data={"error": "job_not_found"},
            )

        # 4. Select submission method
        method = self._select_submission_method(job)

        if method == "manual_required":
            await self._record_failure_activity(
                user_id, "manual_required", job=job
            )
            return AgentOutput(
                action="application_failed",
                rationale="No automated submission method available for this job",
                confidence=0.8,
                data={
                    "error": "manual_required",
                    "job_id": job_id,
                    "job_url": job.get("url"),
                },
            )

        # 5. Prepare materials
        materials = await self._prepare_materials(user_id, job_id)
        if materials is None:
            await self._record_failure_activity(
                user_id, "missing_materials", job=job
            )
            return AgentOutput(
                action="application_failed",
                rationale="No tailored resume found for this job",
                confidence=1.0,
                data={"error": "missing_materials", "job_id": job_id},
            )

        # 6. Record application
        application_id = await self._record_application(
            user_id, job_id, materials["resume_document_id"], method
        )

        # 7. Record activity notification (fire-and-forget)
        try:
            await self._record_submission_activity(
                user_id, job, method, materials, application_id
            )
        except Exception as exc:
            logger.debug("Activity recording failed (non-critical): %s", exc)

        # 8. Build output
        return AgentOutput(
            action="application_submitted",
            rationale=(
                f"Application recorded for {job.get('title', 'unknown')} at "
                f"{job.get('company', 'unknown')} via {method}"
            ),
            confidence=0.9,
            data={
                "application_id": application_id,
                "job_id": job_id,
                "submission_method": method,
                "resume_document_id": materials["resume_document_id"],
                "cover_letter_document_id": materials.get("cover_letter_document_id"),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _check_daily_limit(
        self, user_id: str, tier: str
    ) -> AgentOutput | None:
        """Check if user has reached their daily application limit.

        Returns None if under limit, or an AgentOutput failure if at cap.
        """
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        limit = DAILY_APPLICATION_LIMITS.get(tier, DAILY_APPLICATION_LIMITS["free"])

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM applications "
                    "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                    "AND applied_at >= CURRENT_DATE"
                ),
                {"uid": user_id},
            )
            today_count = result.scalar() or 0

        if today_count >= limit:
            return AgentOutput(
                action="application_failed",
                rationale=f"Daily limit reached ({today_count}/{limit}) for tier '{tier}'",
                confidence=1.0,
                data={
                    "error": "daily_limit_reached",
                    "today_count": today_count,
                    "daily_limit": limit,
                    "tier": tier,
                },
            )

        return None

    async def _load_job(self, job_id: str) -> dict[str, Any] | None:
        """Load job details from the database."""
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT id, title, company, description, location, url, "
                    "salary_min, salary_max, employment_type, remote "
                    "FROM jobs WHERE id = :jid"
                ),
                {"jid": job_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    def _select_submission_method(self, job: dict[str, Any]) -> str:
        """Determine the best submission method for a job.

        Returns:
            'api' if job has an application URL,
            'email_fallback' if description contains email contact,
            'manual_required' if neither is available.
        """
        import re

        # Check for application URL
        url = job.get("url") or ""
        if url:
            return "api"

        # Check for email in description
        description = job.get("description") or ""
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        if re.search(email_pattern, description):
            return "email_fallback"

        return "manual_required"

    async def _prepare_materials(
        self, user_id: str, job_id: str
    ) -> dict[str, Any] | None:
        """Load the latest tailored resume and cover letter for this job.

        Returns dict with document IDs, or None if no resume is available.
        """
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Get latest tailored resume for this job
            resume_result = await session.execute(
                text(
                    "SELECT id FROM documents "
                    "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                    "AND job_id = :jid "
                    "AND type = 'resume' "
                    "AND deleted_at IS NULL "
                    "ORDER BY version DESC LIMIT 1"
                ),
                {"uid": user_id, "jid": job_id},
            )
            resume_row = resume_result.scalar()

            if not resume_row:
                return None

            # Get latest cover letter (optional)
            cl_result = await session.execute(
                text(
                    "SELECT id FROM documents "
                    "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                    "AND job_id = :jid "
                    "AND type = 'cover_letter' "
                    "AND deleted_at IS NULL "
                    "ORDER BY version DESC LIMIT 1"
                ),
                {"uid": user_id, "jid": job_id},
            )
            cl_row = cl_result.scalar()

        return {
            "resume_document_id": str(resume_row),
            "cover_letter_document_id": str(cl_row) if cl_row else None,
        }

    async def _record_application(
        self,
        user_id: str,
        job_id: str,
        resume_document_id: str,
        submission_method: str,
    ) -> str:
        """Record the application in the applications table.

        Returns the new application ID as a string.
        """
        from uuid import uuid4

        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        app_id = str(uuid4())

        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    "INSERT INTO applications (id, user_id, job_id, status, applied_at, resume_version_id) "
                    "VALUES (:id, (SELECT id FROM users WHERE clerk_id = :uid), "
                    ":jid, 'applied', :applied_at, :resume_id)"
                ),
                {
                    "id": app_id,
                    "uid": user_id,
                    "jid": job_id,
                    "applied_at": datetime.now(timezone.utc),
                    "resume_id": resume_document_id,
                },
            )
            await session.commit()

        return app_id

    async def _record_submission_activity(
        self,
        user_id: str,
        job: dict[str, Any],
        method: str,
        materials: dict[str, Any],
        application_id: str,
    ) -> None:
        """Record an agent activity for the successful submission.

        Creates an entry in ``agent_activities`` visible in the activity feed
        and usable for real-time notifications.
        """
        from uuid import uuid4

        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        import json

        activity_data = {
            "application_id": application_id,
            "job_title": job.get("title", "Unknown"),
            "company": job.get("company", "Unknown"),
            "submission_method": method,
            "resume_document_id": materials.get("resume_document_id"),
            "cover_letter_document_id": materials.get("cover_letter_document_id"),
        }

        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    "INSERT INTO agent_activities "
                    "(id, user_id, event_type, agent_type, title, severity, data) "
                    "VALUES (:id, "
                    "(SELECT id FROM users WHERE clerk_id = :uid), "
                    ":event_type, :agent_type, :title, :severity, :data)"
                ),
                {
                    "id": str(uuid4()),
                    "uid": user_id,
                    "event_type": "agent.apply.completed",
                    "agent_type": "apply",
                    "title": (
                        f"Applied to {job.get('title', 'Unknown')} at "
                        f"{job.get('company', 'Unknown')}"
                    ),
                    "severity": "info",
                    "data": json.dumps(activity_data),
                },
            )
            await session.commit()

    async def _record_failure_activity(
        self,
        user_id: str,
        error_reason: str,
        job: dict[str, Any] | None = None,
        job_id: str | None = None,
    ) -> None:
        """Record an agent activity for a failed application attempt.

        Fire-and-forget — failures in recording must not break the main flow.
        """
        try:
            from uuid import uuid4

            from sqlalchemy import text

            from app.db.engine import AsyncSessionLocal

            import json

            job_title = job.get("title", "Unknown") if job else "Unknown"
            company = job.get("company", "Unknown") if job else "Unknown"
            job_url = job.get("url") if job else None

            activity_data = {
                "error": error_reason,
                "job_id": job_id or (str(job["id"]) if job and "id" in job else None),
                "job_title": job_title,
                "company": company,
                "job_url": job_url,
            }

            async with AsyncSessionLocal() as session:
                await session.execute(
                    text(
                        "INSERT INTO agent_activities "
                        "(id, user_id, event_type, agent_type, title, severity, data) "
                        "VALUES (:id, "
                        "(SELECT id FROM users WHERE clerk_id = :uid), "
                        ":event_type, :agent_type, :title, :severity, :data)"
                    ),
                    {
                        "id": str(uuid4()),
                        "uid": user_id,
                        "event_type": "agent.apply.failed",
                        "agent_type": "apply",
                        "title": (
                            f"Application failed for {job_title} at {company}: "
                            f"{error_reason}"
                        ),
                        "severity": "warning",
                        "data": json.dumps(activity_data),
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.debug("Failure activity recording failed (non-critical): %s", exc)
