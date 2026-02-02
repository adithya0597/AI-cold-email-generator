"""At-risk employee detection and re-engagement service.

Identifies employees who may be disengaging based on activity signals:
- Not logged in for 14+ days
- No applications submitted in 30+ days
- Stalled pipeline (no application status changes in 21+ days)

CRITICAL PRIVACY CONSTRAINT: Admin-facing outputs contain ONLY user_id,
name, email, and engagement_status. Never application titles, pipeline
details, job matches, or any individual activity data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, OrganizationMember, User

logger = logging.getLogger(__name__)

# Detection thresholds (days)
LOGIN_INACTIVE_DAYS = 14
APPLICATION_INACTIVE_DAYS = 30
PIPELINE_STALLED_DAYS = 21

EngagementStatus = Literal["at_risk", "active", "placed", "opted_out"]


class AtRiskDetectionService:
    """Service for detecting at-risk employees and returning privacy-safe summaries."""

    async def detect_at_risk(
        self,
        session: AsyncSession,
        org_id: str,
    ) -> List[str]:
        """Detect at-risk user IDs in an organization.

        Evaluates employees against three criteria:
        1. Last login (updated_at proxy) older than 14 days
        2. No applications submitted in 30+ days
        3. No application status changes in 21+ days

        Users matching ANY criterion are considered at-risk.

        Args:
            session: Active async database session.
            org_id: Organization UUID string.

        Returns:
            List of user_id strings flagged as at-risk.
        """
        now = datetime.now(timezone.utc)
        org_uuid = UUID(org_id)

        # Get all member user IDs for the org
        members_result = await session.execute(
            select(OrganizationMember.user_id).where(
                OrganizationMember.org_id == org_uuid
            )
        )
        member_user_ids = [row[0] for row in members_result.all()]

        if not member_user_ids:
            return []

        at_risk_ids: set = set()

        # Criterion 1: Not logged in for 14+ days (using updated_at as proxy)
        login_threshold = now - timedelta(days=LOGIN_INACTIVE_DAYS)
        inactive_login_result = await session.execute(
            select(User.id).where(
                User.id.in_(member_user_ids),
                User.updated_at < login_threshold,
            )
        )
        for row in inactive_login_result.all():
            at_risk_ids.add(str(row[0]))

        # Criterion 2: No applications submitted in 30+ days
        app_threshold = now - timedelta(days=APPLICATION_INACTIVE_DAYS)
        # Find users who HAVE recent applications
        active_applicants_result = await session.execute(
            select(Application.user_id).where(
                Application.user_id.in_(member_user_ids),
                Application.applied_at >= app_threshold,
            ).distinct()
        )
        active_applicant_ids = {row[0] for row in active_applicants_result.all()}

        # Users with NO recent applications are at-risk
        for uid in member_user_ids:
            if uid not in active_applicant_ids:
                at_risk_ids.add(str(uid))

        # Criterion 3: Stalled pipeline (no status changes in 21+ days)
        pipeline_threshold = now - timedelta(days=PIPELINE_STALLED_DAYS)
        # Find users who HAVE recent pipeline activity
        active_pipeline_result = await session.execute(
            select(Application.user_id).where(
                Application.user_id.in_(member_user_ids),
                Application.updated_at >= pipeline_threshold,
            ).distinct()
        )
        active_pipeline_ids = {row[0] for row in active_pipeline_result.all()}

        # Users who have applications but no recent updates are at-risk
        users_with_apps_result = await session.execute(
            select(Application.user_id).where(
                Application.user_id.in_(member_user_ids),
            ).distinct()
        )
        users_with_apps = {row[0] for row in users_with_apps_result.all()}

        for uid in users_with_apps:
            if uid not in active_pipeline_ids:
                at_risk_ids.add(str(uid))

        logger.info(
            "detect_at_risk: org=%s, members=%d, at_risk=%d",
            org_id, len(member_user_ids), len(at_risk_ids),
        )
        return list(at_risk_ids)

    async def get_employee_summaries(
        self,
        session: AsyncSession,
        org_id: str,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return privacy-safe employee summaries for an organization.

        Each record contains ONLY: user_id, name, email, engagement_status.
        NEVER includes application titles, pipeline details, job matches,
        or any individual activity data.

        Args:
            session: Active async database session.
            org_id: Organization UUID string.
            status_filter: Optional filter for engagement status.

        Returns:
            List of dicts with user_id, name, email, engagement_status.
        """
        org_uuid = UUID(org_id)

        # Get members with user info
        result = await session.execute(
            select(
                User.id,
                User.display_name,
                User.email,
            )
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .where(OrganizationMember.org_id == org_uuid)
        )
        members = result.all()

        if not members:
            return []

        # Compute at-risk IDs
        at_risk_ids = set(await self.detect_at_risk(session, org_id))

        summaries = []
        for user_id, display_name, email in members:
            uid_str = str(user_id)
            engagement_status: EngagementStatus = (
                "at_risk" if uid_str in at_risk_ids else "active"
            )

            if status_filter and engagement_status != status_filter:
                continue

            summaries.append({
                "user_id": uid_str,
                "name": display_name or "",
                "email": email,
                "engagement_status": engagement_status,
            })

        return summaries

    async def update_engagement_statuses(
        self,
        session: AsyncSession,
        org_id: str,
    ) -> Dict[str, Any]:
        """Batch evaluate and log engagement statuses for an organization.

        This is called by the daily Celery task. Since engagement_status
        is computed dynamically (not persisted), this method runs detection
        and logs the results for monitoring.

        Args:
            session: Active async database session.
            org_id: Organization UUID string.

        Returns:
            Dict with org_id, total members, and at_risk count.
        """
        org_uuid = UUID(org_id)

        # Count members
        member_count_result = await session.execute(
            select(func.count()).select_from(OrganizationMember).where(
                OrganizationMember.org_id == org_uuid
            )
        )
        total_members = member_count_result.scalar() or 0

        # Detect at-risk
        at_risk_ids = await self.detect_at_risk(session, org_id)

        logger.info(
            "update_engagement_statuses: org=%s, total=%d, at_risk=%d",
            org_id, total_members, len(at_risk_ids),
        )

        return {
            "org_id": org_id,
            "total_members": total_members,
            "at_risk_count": len(at_risk_ids),
        }
