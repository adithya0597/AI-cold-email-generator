"""
Pipeline Agent for JobPilot.

Analyzes email content to detect application status changes (rejection,
interview, offer, etc.) and updates the applications table accordingly.
Creates an audit trail of all detected changes.

The agent receives email content via task_data and does NOT fetch emails
directly — email fetching is handled by OAuth integrations (Stories 6-2, 6-3).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.agents.base import AgentOutput, BaseAgent

logger = logging.getLogger(__name__)


class PipelineAgent(BaseAgent):
    """Detects application status changes from email content."""

    agent_type = "pipeline"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Analyze email content and update application status.

        Expected task_data keys:
            application_id: UUID of the application to check.
            email_subject: Subject line of the email.
            email_body: Body text of the email.
        """
        # 1. Validate inputs
        application_id = task_data.get("application_id")
        email_subject = task_data.get("email_subject", "")
        email_body = task_data.get("email_body", "")

        if not application_id:
            return AgentOutput(
                action="pipeline_failed",
                rationale="No application_id provided",
                confidence=1.0,
                data={"error": "missing_application_id"},
            )

        if not email_subject and not email_body:
            return AgentOutput(
                action="pipeline_failed",
                rationale="No email content provided",
                confidence=1.0,
                data={"error": "empty_email"},
            )

        # 2. Load application from DB
        application = await self._load_application(user_id, application_id)
        if application is None:
            return AgentOutput(
                action="pipeline_failed",
                rationale=f"Application {application_id} not found for user",
                confidence=1.0,
                data={"error": "application_not_found"},
            )

        # 3. Detect status from email
        from app.services.email_parser import EmailStatusDetector

        detector = EmailStatusDetector()
        detection = detector.detect(email_subject, email_body)

        # 4. No status detected
        if detection.detected_status is None:
            return AgentOutput(
                action="pipeline_no_change",
                rationale="No application status signal detected in email",
                confidence=detection.confidence,
                data={
                    "application_id": application_id,
                    "detection": "none",
                },
            )

        # 5. Ambiguous — flag for user review
        if detection.is_ambiguous:
            return AgentOutput(
                action="pipeline_review_needed",
                rationale=(
                    f"Possible {detection.detected_status} detected but confidence "
                    f"too low ({detection.confidence:.2f}) for auto-update"
                ),
                confidence=detection.confidence,
                data={
                    "application_id": application_id,
                    "suggested_status": detection.detected_status,
                    "evidence_snippet": detection.evidence_snippet,
                    "requires_user_review": True,
                },
            )

        old_status = application["status"]

        # 6. Same status — no-op
        if detection.detected_status == old_status:
            return AgentOutput(
                action="pipeline_no_change",
                rationale=f"Detected status '{detection.detected_status}' matches current status",
                confidence=detection.confidence,
                data={
                    "application_id": application_id,
                    "current_status": old_status,
                },
            )

        # 7. Update application status + record audit trail
        await self._update_application_status(
            application_id=application_id,
            old_status=old_status,
            new_status=detection.detected_status,
            confidence=detection.confidence,
            evidence_snippet=detection.evidence_snippet,
            email_subject=email_subject,
        )

        return AgentOutput(
            action="pipeline_status_updated",
            rationale=(
                f"Detected '{detection.detected_status}' from email "
                f"(confidence: {detection.confidence:.2f})"
            ),
            confidence=detection.confidence,
            data={
                "application_id": application_id,
                "old_status": old_status,
                "new_status": detection.detected_status,
                "evidence_snippet": detection.evidence_snippet,
            },
        )

    async def _load_application(
        self, user_id: str, application_id: str
    ) -> dict[str, Any] | None:
        """Load application row for the given user."""
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT a.id, a.status, a.job_id "
                    "FROM applications a "
                    "WHERE a.id = :aid "
                    "AND a.user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                    "AND a.deleted_at IS NULL"
                ),
                {"aid": application_id, "uid": user_id},
            )
            row = result.mappings().first()
            if row is None:
                return None
            return {
                "id": str(row["id"]),
                "status": str(row["status"]).rsplit(".", 1)[-1].lower(),
                "job_id": str(row["job_id"]),
            }

    async def _update_application_status(
        self,
        application_id: str,
        old_status: str,
        new_status: str,
        confidence: float,
        evidence_snippet: str,
        email_subject: str,
    ) -> None:
        """Update application status and insert audit trail record."""
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Update application status
            await session.execute(
                text(
                    "UPDATE applications SET status = :status "
                    "WHERE id = :aid"
                ),
                {"status": new_status, "aid": application_id},
            )

            # Insert status change audit record
            change_id = str(uuid.uuid4())
            await session.execute(
                text(
                    "INSERT INTO application_status_changes "
                    "(id, application_id, old_status, new_status, "
                    "detection_method, confidence, evidence_snippet, "
                    "source_email_subject) "
                    "VALUES (:id, :aid, :old, :new, 'email_parse', "
                    ":conf, :evidence, :subject)"
                ),
                {
                    "id": change_id,
                    "aid": application_id,
                    "old": old_status,
                    "new": new_status,
                    "conf": confidence,
                    "evidence": evidence_snippet,
                    "subject": email_subject,
                },
            )

            await session.commit()
