"""Enterprise metrics service for aggregate organization dashboards.

Computes organization-wide employment outcome metrics without exposing
individual user data. All queries use GROUP BY org_id aggregation and
never SELECT user_id.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Application,
    ApplicationStatus,
    OrganizationMember,
    AgentActivity,
)


@dataclass
class OrgMetrics:
    """Aggregate metrics for an organization — no individual user data."""

    enrolled_count: int
    active_count: int
    jobs_reviewed_count: int
    applications_submitted_count: int
    interviews_scheduled_count: int
    placements_count: int
    placement_rate: float
    avg_time_to_placement_days: float | None


@dataclass
class DailyMetrics:
    """Per-day metric counts for trend visualization."""

    date: str
    applications: int
    interviews: int
    placements: int


class EnterpriseMetricsService:
    """Service for computing aggregate organization metrics.

    Privacy invariant: no method returns individual user_id values.
    All queries aggregate via GROUP BY org_id.
    """

    async def get_aggregate_metrics(
        self,
        session: AsyncSession,
        org_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> OrgMetrics:
        """Return aggregate metrics for the given org and date range.

        Defaults to last 30 days if no dates provided.
        """
        end_date = end_date or date.today()
        start_date = start_date or (end_date - timedelta(days=30))

        start_dt = datetime(start_date.year, start_date.month, start_date.day)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        enrolled = await self._count_enrolled(session, org_uuid)
        active = await self._count_active(session, org_uuid, start_dt, end_dt)
        jobs_reviewed = await self._count_jobs_reviewed(session, org_uuid, start_dt, end_dt)
        applications = await self._count_applications(session, org_uuid, start_dt, end_dt)
        interviews = await self._count_interviews(session, org_uuid, start_dt, end_dt)
        placements = await self._count_placements(session, org_uuid, start_dt, end_dt)
        placement_rate = self._calc_placement_rate(placements, applications)
        avg_time = await self._calc_avg_time_to_placement(session, org_uuid, start_dt, end_dt)

        return OrgMetrics(
            enrolled_count=enrolled,
            active_count=active,
            jobs_reviewed_count=jobs_reviewed,
            applications_submitted_count=applications,
            interviews_scheduled_count=interviews,
            placements_count=placements,
            placement_rate=placement_rate,
            avg_time_to_placement_days=avg_time,
        )

    async def get_daily_breakdown(
        self,
        session: AsyncSession,
        org_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[DailyMetrics]:
        """Return per-day counts for applications, interviews, and placements.

        Uses DATE_TRUNC('day', ...) GROUP BY for aggregation.
        """
        end_date = end_date or date.today()
        start_date = start_date or (end_date - timedelta(days=30))

        start_dt = datetime(start_date.year, start_date.month, start_date.day)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        # Subquery: members of this org
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
            .correlate_except(OrganizationMember)
            .scalar_subquery()
        )

        day_col = func.date_trunc("day", Application.applied_at).label("day")

        stmt = (
            select(
                day_col,
                func.count(Application.id).label("total_apps"),
                func.count(
                    Application.id
                ).filter(
                    Application.status.in_([
                        ApplicationStatus.INTERVIEW,
                        ApplicationStatus.OFFER,
                    ])
                ).label("interviews"),
                func.count(
                    Application.id
                ).filter(
                    Application.status == ApplicationStatus.OFFER
                ).label("placements"),
            )
            .where(
                Application.user_id.in_(member_subq),
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
            .group_by(day_col)
            .order_by(day_col)
        )

        result = await session.execute(stmt)
        rows = result.all()

        return [
            DailyMetrics(
                date=row.day.strftime("%Y-%m-%d") if row.day else "",
                applications=row.total_apps,
                interviews=row.interviews,
                placements=row.placements,
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Private aggregate query methods
    # ------------------------------------------------------------------

    async def _count_enrolled(self, session: AsyncSession, org_uuid: UUID) -> int:
        """Count all members in the organization (GROUP BY org_id)."""
        stmt = (
            select(func.count(OrganizationMember.id))
            .where(OrganizationMember.org_id == org_uuid)
            .group_by(OrganizationMember.org_id)
        )
        result = await session.execute(stmt)
        row = result.scalar()
        return row or 0

    async def _count_active(
        self, session: AsyncSession, org_uuid: UUID, start_dt: datetime, end_dt: datetime
    ) -> int:
        """Count org members who have any application activity in the date range.

        Uses a subquery to find distinct users with applications, then counts
        by org_id — never exposes individual user_id in the outer SELECT.
        """
        # Subquery: member user_ids for this org
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
            .correlate_except(OrganizationMember)
            .scalar_subquery()
        )

        stmt = (
            select(func.count(func.distinct(Application.user_id)))
            .where(
                Application.user_id.in_(
                    select(OrganizationMember.user_id).where(
                        OrganizationMember.org_id == org_uuid
                    )
                ),
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def _count_jobs_reviewed(
        self, session: AsyncSession, org_uuid: UUID, start_dt: datetime, end_dt: datetime
    ) -> int:
        """Count job review activities for org members (GROUP BY org_id aggregation).

        Uses AgentActivity with event_type 'job_review' as the data source.
        Falls back to 0 if no such activity exists.
        """
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
        )

        stmt = (
            select(func.count(AgentActivity.id))
            .where(
                AgentActivity.user_id.in_(member_subq),
                AgentActivity.event_type == "job_review",
                AgentActivity.created_at >= start_dt,
                AgentActivity.created_at <= end_dt,
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def _count_applications(
        self, session: AsyncSession, org_uuid: UUID, start_dt: datetime, end_dt: datetime
    ) -> int:
        """Count applications submitted by org members in date range."""
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
        )

        stmt = (
            select(func.count(Application.id))
            .where(
                Application.user_id.in_(member_subq),
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def _count_interviews(
        self, session: AsyncSession, org_uuid: UUID, start_dt: datetime, end_dt: datetime
    ) -> int:
        """Count applications in interview or later status for org members."""
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
        )

        stmt = (
            select(func.count(Application.id))
            .where(
                Application.user_id.in_(member_subq),
                Application.status.in_([
                    ApplicationStatus.INTERVIEW,
                    ApplicationStatus.OFFER,
                ]),
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def _count_placements(
        self, session: AsyncSession, org_uuid: UUID, start_dt: datetime, end_dt: datetime
    ) -> int:
        """Count applications with OFFER status for org members."""
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
        )

        stmt = (
            select(func.count(Application.id))
            .where(
                Application.user_id.in_(member_subq),
                Application.status == ApplicationStatus.OFFER,
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    def _calc_placement_rate(placements: int, applications: int) -> float:
        """Calculate placement rate as percentage."""
        if applications == 0:
            return 0.0
        return round((placements / applications) * 100, 2)

    async def _calc_avg_time_to_placement(
        self, session: AsyncSession, org_uuid: UUID, start_dt: datetime, end_dt: datetime
    ) -> float | None:
        """Calculate average days from enrollment to placement for org members.

        Uses the difference between Application.updated_at (when status changed
        to OFFER) and OrganizationMember.created_at (enrollment date).
        Returns None if no placements exist.
        """
        member_subq = (
            select(OrganizationMember.user_id, OrganizationMember.created_at.label("enrolled_at"))
            .where(OrganizationMember.org_id == org_uuid)
            .subquery()
        )

        # Average days between enrollment and placement (updated_at approximates offer date)
        days_expr = func.avg(
            func.extract("epoch", Application.updated_at) -
            func.extract("epoch", member_subq.c.enrolled_at)
        ) / 86400.0  # seconds to days

        stmt = (
            select(days_expr.label("avg_days"))
            .select_from(Application)
            .join(member_subq, Application.user_id == member_subq.c.user_id)
            .where(
                Application.status == ApplicationStatus.OFFER,
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
        )
        result = await session.execute(stmt)
        avg_days = result.scalar()
        return round(float(avg_days), 1) if avg_days is not None else None
