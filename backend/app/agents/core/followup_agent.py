"""
Follow-up Agent for JobPilot.

Evaluates applications to determine when follow-ups are due, generates
draft follow-up messages via LLM, and stores suggestions for user review.

Timing rules (business days):
  - After application submitted: 5-7 business days
  - After interview: 1-2 business days
  - After no response (generic): 14 calendar days (~10 business days)

Aggressiveness preference adjusts timing:
  - conservative: +50% more days
  - normal: default timing
  - aggressive: -30% fewer days
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.agents.base import AgentOutput, BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Timing constants (business days)
# ---------------------------------------------------------------------------

TIMING_RULES: dict[str, int] = {
    "applied": 6,       # 5-7 business days → midpoint 6
    "interview": 2,     # 1-2 business days → midpoint 2
    "screening": 10,    # ~2 weeks of business days
}

AGGRESSIVENESS_MULTIPLIERS: dict[str, float] = {
    "conservative": 1.5,
    "normal": 1.0,
    "aggressive": 0.7,
}


def _add_business_days(start: datetime, bdays: int) -> datetime:
    """Add *bdays* business days to *start*, skipping weekends."""
    current = start
    added = 0
    while added < bdays:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            added += 1
    return current


class FollowUpAgent(BaseAgent):
    """Suggests timely follow-ups for pipeline applications."""

    agent_type = "followup"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Scan user applications and generate follow-up suggestions.

        Optional task_data keys:
            aggressiveness: 'conservative' | 'normal' | 'aggressive' (default 'normal')
        """
        aggressiveness = task_data.get("aggressiveness", "normal")

        # 1. Load applications needing follow-up evaluation
        applications = await self._load_pending_applications(user_id)

        if not applications:
            return AgentOutput(
                action="followup_none_needed",
                rationale="No applications currently need follow-up",
                confidence=1.0,
                data={"suggestions_count": 0},
            )

        now = datetime.now(timezone.utc)
        suggestions: list[dict[str, Any]] = []

        for app in applications:
            followup_date = self._calculate_followup_date(app, aggressiveness)
            if followup_date is None or now < followup_date:
                continue

            # Generate draft message
            draft = await self._generate_followup_draft(app)

            suggestion = {
                "id": str(uuid.uuid4()),
                "application_id": app["id"],
                "company": app["company"],
                "job_title": app["job_title"],
                "status": app["status"],
                "followup_date": followup_date.isoformat(),
                "draft_subject": draft["subject"],
                "draft_body": draft["body"],
            }
            suggestions.append(suggestion)

        # 2. Store suggestions
        if suggestions:
            await self._store_suggestions(user_id, suggestions)

        return AgentOutput(
            action="followup_suggestions_created",
            rationale=f"Generated {len(suggestions)} follow-up suggestions",
            confidence=0.85,
            data={
                "suggestions_count": len(suggestions),
                "suggestions": suggestions,
            },
        )

    def _calculate_followup_date(
        self, app: dict[str, Any], aggressiveness: str
    ) -> datetime | None:
        """Calculate when a follow-up is due for this application."""
        status = app["status"]
        base_days = TIMING_RULES.get(status)
        if base_days is None:
            return None

        multiplier = AGGRESSIVENESS_MULTIPLIERS.get(aggressiveness, 1.0)
        adjusted_days = max(1, round(base_days * multiplier))

        # Use updated_at if available, else applied_at
        ref_date_str = app.get("updated_at") or app["applied_at"]
        ref_date = datetime.fromisoformat(ref_date_str.replace("Z", "+00:00"))

        return _add_business_days(ref_date, adjusted_days)

    async def _generate_followup_draft(self, app: dict[str, Any]) -> dict[str, str]:
        """Generate a follow-up email draft via LLM."""
        company = app.get("company") or "the company"
        job_title = app.get("job_title") or "the position"
        status = app["status"]

        prompt = (
            f"Write a brief, professional follow-up email for a job application.\n\n"
            f"Company: {company}\n"
            f"Position: {job_title}\n"
            f"Current status: {status}\n\n"
            f"Requirements:\n"
            f"- Appropriate subject line\n"
            f"- Reference the original application\n"
            f"- Polite status inquiry\n"
            f"- Restatement of interest\n"
            f"- Keep under 150 words\n\n"
            f"Return JSON with keys: subject, body"
        )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI()
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300,
            )

            import json

            content = response.choices[0].message.content or ""
            # Strip markdown code fences if present
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
            return {
                "subject": result.get("subject", f"Following up on {job_title} application"),
                "body": result.get("body", ""),
            }
        except Exception:
            logger.warning("LLM draft generation failed, using template fallback")
            return {
                "subject": f"Following up on my {job_title} application",
                "body": (
                    f"Dear Hiring Team,\n\n"
                    f"I hope this message finds you well. I wanted to follow up on my "
                    f"application for the {job_title} position at {company}. I remain very "
                    f"interested in the opportunity and would welcome the chance to discuss "
                    f"how my experience aligns with your needs.\n\n"
                    f"Thank you for your time and consideration.\n\n"
                    f"Best regards"
                ),
            }

    async def _load_pending_applications(self, user_id: str) -> list[dict[str, Any]]:
        """Load applications that may need follow-up."""
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT a.id, a.status, a.applied_at, a.updated_at, "
                    "j.title AS job_title, j.company "
                    "FROM applications a "
                    "JOIN jobs j ON j.id = a.job_id "
                    "WHERE a.user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                    "AND a.deleted_at IS NULL "
                    "AND a.status IN ('applied', 'screening', 'interview') "
                    "AND a.id NOT IN ("
                    "  SELECT fs.application_id FROM followup_suggestions fs "
                    "  WHERE fs.dismissed_at IS NULL"
                    ")"
                ),
                {"uid": user_id},
            )
            rows = result.mappings().all()
            return [
                {
                    "id": str(row["id"]),
                    "status": str(row["status"]),
                    "applied_at": str(row["applied_at"]),
                    "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
                    "job_title": str(row["job_title"]) if row["job_title"] else None,
                    "company": str(row["company"]) if row["company"] else None,
                }
                for row in rows
            ]

    async def _store_suggestions(
        self, user_id: str, suggestions: list[dict[str, Any]]
    ) -> None:
        """Persist follow-up suggestions to the database."""
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Ensure table exists
            await session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS followup_suggestions ("
                    "  id UUID PRIMARY KEY, "
                    "  user_id UUID NOT NULL, "
                    "  application_id UUID NOT NULL, "
                    "  company TEXT, "
                    "  job_title TEXT, "
                    "  status TEXT, "
                    "  followup_date TIMESTAMPTZ, "
                    "  draft_subject TEXT, "
                    "  draft_body TEXT, "
                    "  dismissed_at TIMESTAMPTZ, "
                    "  created_at TIMESTAMPTZ DEFAULT NOW()"
                    ")"
                )
            )

            for s in suggestions:
                await session.execute(
                    text(
                        "INSERT INTO followup_suggestions "
                        "(id, user_id, application_id, company, job_title, "
                        "status, followup_date, draft_subject, draft_body) "
                        "VALUES (:id, "
                        "(SELECT id FROM users WHERE clerk_id = :uid), "
                        ":app_id, :company, :title, :status, "
                        ":fdate, :subject, :body)"
                    ),
                    {
                        "id": s["id"],
                        "uid": user_id,
                        "app_id": s["application_id"],
                        "company": s["company"],
                        "title": s["job_title"],
                        "status": s["status"],
                        "fdate": s["followup_date"],
                        "subject": s["draft_subject"],
                        "body": s["draft_body"],
                    },
                )

            await session.commit()
