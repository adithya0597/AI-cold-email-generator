"""ROI Report service for enterprise program value metrics.

Computes cost-per-placement, time-to-placement, engagement rate, and
satisfaction score using privacy-safe aggregate queries (COUNT, AVG, SUM
only). Provides benchmark comparisons against configurable industry defaults.

Privacy invariant: no method returns individual user data.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Application,
    ApplicationStatus,
    Organization,
    OrganizationMember,
)


class ROIReportService:
    """Compute ROI metrics for an organization's career transition program.

    All queries use aggregate functions (COUNT, AVG, SUM) only.
    No individual user data is returned.
    """

    # Industry benchmark defaults (overridable per-org via Organization.settings)
    TIME_TO_PLACEMENT_BENCHMARK = 90  # days (traditional outplacement average)
    ENGAGEMENT_RATE_BENCHMARK = 0.35  # 35% (traditional outplacement average)
    COST_PER_PLACEMENT_BENCHMARK = 15000.0  # dollars
    SATISFACTION_SCORE_BENCHMARK = 3.5  # out of 5

    async def compute_metrics(
        self,
        session: AsyncSession,
        org_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Compute all ROI metrics for the given org and date range.

        Defaults to current calendar month if no dates provided.
        Returns a dict with metric values and benchmark comparisons.
        """
        today = date.today()
        if start_date is None:
            start_date = today.replace(day=1)
        if end_date is None:
            end_date = today

        start_dt = datetime(start_date.year, start_date.month, start_date.day)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        cost_per_placement = await self._compute_cost_per_placement(
            session, org_uuid, start_dt, end_dt
        )
        time_to_placement = await self._compute_time_to_placement(
            session, org_uuid, start_dt, end_dt
        )
        engagement_rate = await self._compute_engagement_rate(
            session, org_uuid, start_dt, end_dt
        )
        satisfaction_score = await self._compute_satisfaction_score(
            session, org_uuid, start_dt, end_dt
        )

        metrics = {
            "cost_per_placement": cost_per_placement,
            "time_to_placement_days": time_to_placement,
            "engagement_rate": engagement_rate,
            "satisfaction_score": satisfaction_score,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        # Load org-specific benchmark overrides
        benchmarks = await self._load_org_benchmarks(session, org_uuid)
        metrics["benchmarks"] = self.add_benchmarks(metrics, benchmarks)

        return metrics

    async def _compute_cost_per_placement(
        self,
        session: AsyncSession,
        org_uuid: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> float | None:
        """Total program cost / number of placements in period.

        Uses COUNT(members) * assumed seat cost from Organization.settings.
        Falls back to enrolled member count * default seat cost if not configured.
        """
        # Count placements in period
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
        )

        placement_stmt = (
            select(func.count(Application.id))
            .where(
                Application.user_id.in_(member_subq),
                Application.status == ApplicationStatus.OFFER,
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
        )
        result = await session.execute(placement_stmt)
        placements = result.scalar() or 0

        if placements == 0:
            return None

        # Count enrolled members for cost calculation
        enrolled_stmt = (
            select(func.count(OrganizationMember.id))
            .where(OrganizationMember.org_id == org_uuid)
        )
        result = await session.execute(enrolled_stmt)
        enrolled = result.scalar() or 0

        # Load seat cost from org settings or use default
        org_stmt = select(Organization.settings).where(Organization.id == org_uuid)
        result = await session.execute(org_stmt)
        settings = result.scalar() or {}
        seat_cost = (settings.get("seat_cost_monthly") or 500.0)

        total_cost = enrolled * seat_cost
        return round(total_cost / placements, 2)

    async def _compute_time_to_placement(
        self,
        session: AsyncSession,
        org_uuid: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> float | None:
        """AVG days from enrollment to placement for placed users in period.

        Uses the difference between Application.updated_at (when status changed
        to OFFER) and OrganizationMember.created_at (enrollment date).
        Returns None if no placements exist.
        """
        member_subq = (
            select(
                OrganizationMember.user_id,
                OrganizationMember.created_at.label("enrolled_at"),
            )
            .where(OrganizationMember.org_id == org_uuid)
            .subquery()
        )

        days_expr = func.avg(
            func.extract("epoch", Application.updated_at)
            - func.extract("epoch", member_subq.c.enrolled_at)
        ) / 86400.0

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

    async def _compute_engagement_rate(
        self,
        session: AsyncSession,
        org_uuid: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> float:
        """Active users / enrolled users in period.

        Active = users with at least one application in the date range.
        Returns 0.0 if no enrolled users.
        """
        # Total enrolled
        enrolled_stmt = (
            select(func.count(OrganizationMember.id))
            .where(OrganizationMember.org_id == org_uuid)
        )
        result = await session.execute(enrolled_stmt)
        enrolled = result.scalar() or 0

        if enrolled == 0:
            return 0.0

        # Active (distinct users with applications in period)
        member_subq = (
            select(OrganizationMember.user_id)
            .where(OrganizationMember.org_id == org_uuid)
        )

        active_stmt = (
            select(func.count(func.distinct(Application.user_id)))
            .where(
                Application.user_id.in_(member_subq),
                Application.applied_at >= start_dt,
                Application.applied_at <= end_dt,
            )
        )
        result = await session.execute(active_stmt)
        active = result.scalar() or 0

        return round(active / enrolled, 4)

    async def _compute_satisfaction_score(
        self,
        session: AsyncSession,
        org_uuid: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> float | None:
        """AVG satisfaction rating from feedback.

        Stub: returns None until a feedback table is implemented.
        When feedback table exists, will use AVG(rating) for org members.
        """
        # No feedback table exists yet -- return None as placeholder
        return None

    async def _load_org_benchmarks(
        self, session: AsyncSession, org_uuid: UUID
    ) -> dict[str, float]:
        """Load org-specific benchmark overrides from Organization.settings.

        Returns merged dict of defaults + overrides.
        """
        defaults = {
            "time_to_placement_days": self.TIME_TO_PLACEMENT_BENCHMARK,
            "engagement_rate": self.ENGAGEMENT_RATE_BENCHMARK,
            "cost_per_placement": self.COST_PER_PLACEMENT_BENCHMARK,
            "satisfaction_score": self.SATISFACTION_SCORE_BENCHMARK,
        }

        stmt = select(Organization.settings).where(Organization.id == org_uuid)
        result = await session.execute(stmt)
        settings = result.scalar() or {}

        org_benchmarks = settings.get("benchmarks") or {}
        merged = {**defaults, **org_benchmarks}
        return merged

    def add_benchmarks(
        self,
        metrics: dict[str, Any],
        benchmarks: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Add benchmark comparison data to metrics.

        For each metric, adds:
        - benchmark_value: the benchmark number
        - comparison: 'better' | 'at_benchmark' | 'worse'

        Uses class constant defaults if no benchmarks dict provided.
        """
        if benchmarks is None:
            benchmarks = {
                "time_to_placement_days": self.TIME_TO_PLACEMENT_BENCHMARK,
                "engagement_rate": self.ENGAGEMENT_RATE_BENCHMARK,
                "cost_per_placement": self.COST_PER_PLACEMENT_BENCHMARK,
                "satisfaction_score": self.SATISFACTION_SCORE_BENCHMARK,
            }

        result: dict[str, Any] = {}

        # Time to placement: lower is better
        ttp = metrics.get("time_to_placement_days")
        ttp_bench = benchmarks.get("time_to_placement_days", self.TIME_TO_PLACEMENT_BENCHMARK)
        result["time_to_placement_days"] = {
            "benchmark_value": ttp_bench,
            "comparison": self._compare_lower_better(ttp, ttp_bench),
        }

        # Cost per placement: lower is better
        cpp = metrics.get("cost_per_placement")
        cpp_bench = benchmarks.get("cost_per_placement", self.COST_PER_PLACEMENT_BENCHMARK)
        result["cost_per_placement"] = {
            "benchmark_value": cpp_bench,
            "comparison": self._compare_lower_better(cpp, cpp_bench),
        }

        # Engagement rate: higher is better
        er = metrics.get("engagement_rate")
        er_bench = benchmarks.get("engagement_rate", self.ENGAGEMENT_RATE_BENCHMARK)
        result["engagement_rate"] = {
            "benchmark_value": er_bench,
            "comparison": self._compare_higher_better(er, er_bench),
        }

        # Satisfaction score: higher is better
        ss = metrics.get("satisfaction_score")
        ss_bench = benchmarks.get("satisfaction_score", self.SATISFACTION_SCORE_BENCHMARK)
        result["satisfaction_score"] = {
            "benchmark_value": ss_bench,
            "comparison": self._compare_higher_better(ss, ss_bench),
        }

        return result

    @staticmethod
    def _compare_lower_better(value: float | None, benchmark: float) -> str:
        """Compare where lower values are better (time, cost)."""
        if value is None:
            return "no_data"
        if value < benchmark * 0.9:
            return "better"
        if value <= benchmark * 1.1:
            return "at_benchmark"
        return "worse"

    @staticmethod
    def _compare_higher_better(value: float | None, benchmark: float) -> str:
        """Compare where higher values are better (engagement, satisfaction)."""
        if value is None:
            return "no_data"
        if value > benchmark * 1.1:
            return "better"
        if value >= benchmark * 0.9:
            return "at_benchmark"
        return "worse"

    async def get_schedule(
        self, session: AsyncSession, org_id: str
    ) -> dict[str, Any]:
        """Get the ROI report schedule config from Organization.settings."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
        stmt = select(Organization.settings).where(Organization.id == org_uuid)
        result = await session.execute(stmt)
        settings = result.scalar() or {}
        return settings.get("roi_report_schedule") or {
            "enabled": False,
            "recipients": [],
        }

    async def save_schedule(
        self,
        session: AsyncSession,
        org_id: str,
        schedule_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Save ROI report schedule config to Organization.settings.

        Merges into existing settings JSONB under key 'roi_report_schedule'.
        """
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        stmt = select(Organization).where(Organization.id == org_uuid)
        result = await session.execute(stmt)
        org = result.scalar_one()

        current_settings = org.settings or {}
        current_settings["roi_report_schedule"] = {
            "enabled": schedule_config.get("enabled", False),
            "recipients": schedule_config.get("recipients", []),
        }
        org.settings = current_settings

        await session.flush()
        return current_settings["roi_report_schedule"]
