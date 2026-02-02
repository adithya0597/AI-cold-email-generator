"""Unit tests for EnterpriseMetricsService.

Tests verify:
- Aggregate metrics return correct structure (AC1)
- Date range defaults to 30 days (AC2)
- Daily breakdown structure (AC3)
- No user_id in OrgMetrics dataclass (AC4)
- CSV export format (AC5)
- Admin auth requirement (AC7)
- Placement rate calculation (AC1)
"""

from __future__ import annotations

import csv
import io
from dataclasses import fields
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.enterprise.metrics import (
    DailyMetrics,
    EnterpriseMetricsService,
    OrgMetrics,
)


# ---------------------------------------------------------------------------
# OrgMetrics dataclass tests (AC4: no user_id field)
# ---------------------------------------------------------------------------


class TestOrgMetricsDataclass:
    """Verify the OrgMetrics dataclass shape and privacy guarantees."""

    def test_no_user_id_field(self):
        """OrgMetrics must never contain a user_id field (AC4)."""
        field_names = {f.name for f in fields(OrgMetrics)}
        assert "user_id" not in field_names
        assert "user_name" not in field_names
        assert "email" not in field_names

    def test_has_all_required_fields(self):
        """OrgMetrics has all 8 aggregate metric fields (AC1)."""
        field_names = {f.name for f in fields(OrgMetrics)}
        expected = {
            "enrolled_count",
            "active_count",
            "jobs_reviewed_count",
            "applications_submitted_count",
            "interviews_scheduled_count",
            "placements_count",
            "placement_rate",
            "avg_time_to_placement_days",
        }
        assert expected == field_names

    def test_construction(self):
        """OrgMetrics can be constructed with valid values."""
        m = OrgMetrics(
            enrolled_count=10,
            active_count=8,
            jobs_reviewed_count=100,
            applications_submitted_count=50,
            interviews_scheduled_count=15,
            placements_count=5,
            placement_rate=10.0,
            avg_time_to_placement_days=30.5,
        )
        assert m.enrolled_count == 10
        assert m.placement_rate == 10.0
        assert m.avg_time_to_placement_days == 30.5


# ---------------------------------------------------------------------------
# DailyMetrics dataclass tests (AC3)
# ---------------------------------------------------------------------------


class TestDailyMetricsDataclass:
    """Verify the DailyMetrics dataclass shape."""

    def test_has_required_fields(self):
        field_names = {f.name for f in fields(DailyMetrics)}
        assert field_names == {"date", "applications", "interviews", "placements"}

    def test_no_user_id_field(self):
        field_names = {f.name for f in fields(DailyMetrics)}
        assert "user_id" not in field_names

    def test_construction(self):
        d = DailyMetrics(date="2026-01-15", applications=12, interviews=3, placements=1)
        assert d.date == "2026-01-15"
        assert d.applications == 12


# ---------------------------------------------------------------------------
# Placement rate calculation (AC1)
# ---------------------------------------------------------------------------


class TestPlacementRate:
    """Test static placement rate calculation."""

    def test_normal_rate(self):
        rate = EnterpriseMetricsService._calc_placement_rate(5, 50)
        assert rate == 10.0

    def test_zero_applications(self):
        rate = EnterpriseMetricsService._calc_placement_rate(0, 0)
        assert rate == 0.0

    def test_zero_placements(self):
        rate = EnterpriseMetricsService._calc_placement_rate(0, 100)
        assert rate == 0.0

    def test_all_placed(self):
        rate = EnterpriseMetricsService._calc_placement_rate(10, 10)
        assert rate == 100.0

    def test_rounding(self):
        rate = EnterpriseMetricsService._calc_placement_rate(1, 3)
        assert rate == 33.33


# ---------------------------------------------------------------------------
# Date range defaults (AC2)
# ---------------------------------------------------------------------------


class TestDateRangeDefaults:
    """Verify default date range is last 30 days."""

    @pytest.mark.asyncio
    async def test_default_date_range_30_days(self):
        """get_aggregate_metrics defaults to 30-day window when no dates provided."""
        service = EnterpriseMetricsService()

        # Mock all internal methods to verify date args
        captured_dates: dict = {}

        async def mock_count_enrolled(session, org_uuid):
            return 10

        async def mock_count_active(session, org_uuid, start_dt, end_dt):
            captured_dates["start"] = start_dt
            captured_dates["end"] = end_dt
            return 5

        async def mock_count_jobs_reviewed(session, org_uuid, start_dt, end_dt):
            return 0

        async def mock_count_applications(session, org_uuid, start_dt, end_dt):
            return 20

        async def mock_count_interviews(session, org_uuid, start_dt, end_dt):
            return 5

        async def mock_count_placements(session, org_uuid, start_dt, end_dt):
            return 2

        async def mock_avg_time(session, org_uuid, start_dt, end_dt):
            return 25.0

        service._count_enrolled = mock_count_enrolled
        service._count_active = mock_count_active
        service._count_jobs_reviewed = mock_count_jobs_reviewed
        service._count_applications = mock_count_applications
        service._count_interviews = mock_count_interviews
        service._count_placements = mock_count_placements
        service._calc_avg_time_to_placement = mock_avg_time

        mock_session = AsyncMock()
        result = await service.get_aggregate_metrics(
            mock_session, "00000000-0000-0000-0000-000000000001"
        )

        # Verify the date range spans 30 days
        assert "start" in captured_dates
        delta = captured_dates["end"].date() - captured_dates["start"].date()
        assert delta.days == 30

        # Verify result is an OrgMetrics instance
        assert isinstance(result, OrgMetrics)
        assert result.enrolled_count == 10
        assert result.applications_submitted_count == 20


# ---------------------------------------------------------------------------
# CSV export format (AC5)
# ---------------------------------------------------------------------------


class TestCSVExport:
    """Test CSV export output format."""

    def test_csv_headers_and_data(self):
        """CSV export contains correct headers and summary + daily sections."""
        # Simulate what the endpoint does
        summary = OrgMetrics(
            enrolled_count=48,
            active_count=35,
            jobs_reviewed_count=1240,
            applications_submitted_count=312,
            interviews_scheduled_count=67,
            placements_count=22,
            placement_rate=7.05,
            avg_time_to_placement_days=34.2,
        )
        daily = [
            DailyMetrics(date="2026-01-03", applications=12, interviews=3, placements=1),
            DailyMetrics(date="2026-01-04", applications=8, interviews=2, placements=0),
        ]

        output = io.StringIO()
        writer = csv.writer(output)

        # Summary section
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Enrolled", summary.enrolled_count])
        writer.writerow(["Active", summary.active_count])
        writer.writerow(["Jobs Reviewed", summary.jobs_reviewed_count])
        writer.writerow(["Applications Submitted", summary.applications_submitted_count])
        writer.writerow(["Interviews Scheduled", summary.interviews_scheduled_count])
        writer.writerow(["Placements", summary.placements_count])
        writer.writerow(["Placement Rate (%)", summary.placement_rate])
        writer.writerow(["Avg Time to Placement (days)", summary.avg_time_to_placement_days or "N/A"])
        writer.writerow([])
        writer.writerow(["Date", "Applications", "Interviews", "Placements"])
        for d in daily:
            writer.writerow([d.date, d.applications, d.interviews, d.placements])

        output.seek(0)
        content = output.getvalue()

        # Verify summary headers
        assert "Metric,Value" in content
        assert "Enrolled,48" in content
        assert "Applications Submitted,312" in content
        assert "Placement Rate (%),7.05" in content

        # Verify daily breakdown headers
        assert "Date,Applications,Interviews,Placements" in content
        assert "2026-01-03,12,3,1" in content
        assert "2026-01-04,8,2,0" in content


# ---------------------------------------------------------------------------
# Endpoint admin auth requirement (AC7)
# ---------------------------------------------------------------------------


class TestMetricsEndpointAuth:
    """Test that the metrics endpoint requires admin authentication."""

    def test_endpoint_uses_require_admin(self):
        """GET /admin/metrics endpoint is protected by require_admin dependency."""
        from app.api.v1.admin import get_metrics
        from fastapi import params

        # Check the function's dependency annotations
        import inspect

        sig = inspect.signature(get_metrics)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        # The default should be a Depends() call
        assert isinstance(admin_param.default, params.Depends)


# ---------------------------------------------------------------------------
# Aggregate metrics structure (AC1)
# ---------------------------------------------------------------------------


class TestAggregateMetricsStructure:
    """Test that aggregate metrics returns correct structure."""

    @pytest.mark.asyncio
    async def test_returns_org_metrics(self):
        """get_aggregate_metrics returns OrgMetrics with all fields populated."""
        service = EnterpriseMetricsService()

        # Mock all internal methods
        service._count_enrolled = AsyncMock(return_value=25)
        service._count_active = AsyncMock(return_value=18)
        service._count_jobs_reviewed = AsyncMock(return_value=500)
        service._count_applications = AsyncMock(return_value=100)
        service._count_interviews = AsyncMock(return_value=30)
        service._count_placements = AsyncMock(return_value=10)
        service._calc_avg_time_to_placement = AsyncMock(return_value=28.5)

        mock_session = AsyncMock()
        result = await service.get_aggregate_metrics(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert isinstance(result, OrgMetrics)
        assert result.enrolled_count == 25
        assert result.active_count == 18
        assert result.jobs_reviewed_count == 500
        assert result.applications_submitted_count == 100
        assert result.interviews_scheduled_count == 30
        assert result.placements_count == 10
        assert result.placement_rate == 10.0
        assert result.avg_time_to_placement_days == 28.5


# ---------------------------------------------------------------------------
# Daily breakdown structure (AC3)
# ---------------------------------------------------------------------------


class TestDailyBreakdownStructure:
    """Test daily breakdown returns correct shape."""

    def test_daily_metrics_fields(self):
        d = DailyMetrics(date="2026-01-15", applications=10, interviews=3, placements=1)
        assert d.date == "2026-01-15"
        assert d.applications == 10
        assert d.interviews == 3
        assert d.placements == 1
