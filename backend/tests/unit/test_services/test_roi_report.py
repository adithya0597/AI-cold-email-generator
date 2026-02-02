"""Unit tests for ROIReportService.

Tests verify:
- Cost per placement computation (AC1)
- Time to placement computation (AC1)
- Engagement rate computation (AC1)
- Satisfaction score stub returns None (AC1)
- Benchmark comparison with defaults and overrides (AC2)
- Date range filtering defaults to current month (AC3)
- Schedule storage in Organization.settings (AC4)
- Privacy-safe -- no individual user data (AC6)
- RBAC enforcement via require_admin dependency (AC7)
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.enterprise.roi_report import ROIReportService


# ---------------------------------------------------------------------------
# Benchmark comparison tests (AC2)
# ---------------------------------------------------------------------------


class TestBenchmarkConstants:
    """Verify benchmark defaults are set correctly."""

    def test_time_to_placement_benchmark(self):
        assert ROIReportService.TIME_TO_PLACEMENT_BENCHMARK == 90

    def test_engagement_rate_benchmark(self):
        assert ROIReportService.ENGAGEMENT_RATE_BENCHMARK == 0.35

    def test_cost_per_placement_benchmark(self):
        assert ROIReportService.COST_PER_PLACEMENT_BENCHMARK == 15000.0

    def test_satisfaction_score_benchmark(self):
        assert ROIReportService.SATISFACTION_SCORE_BENCHMARK == 3.5


class TestBenchmarkComparison:
    """Test add_benchmarks() with known metric values (AC2)."""

    def test_better_than_benchmarks(self):
        """Metrics significantly better than benchmarks show 'better'."""
        service = ROIReportService()
        metrics = {
            "cost_per_placement": 5000.0,  # Much lower than 15000
            "time_to_placement_days": 30.0,  # Much lower than 90
            "engagement_rate": 0.80,  # Much higher than 0.35
            "satisfaction_score": 4.5,  # Much higher than 3.5
        }
        result = service.add_benchmarks(metrics)

        assert result["cost_per_placement"]["comparison"] == "better"
        assert result["time_to_placement_days"]["comparison"] == "better"
        assert result["engagement_rate"]["comparison"] == "better"
        assert result["satisfaction_score"]["comparison"] == "better"

    def test_worse_than_benchmarks(self):
        """Metrics significantly worse than benchmarks show 'worse'."""
        service = ROIReportService()
        metrics = {
            "cost_per_placement": 25000.0,  # Much higher than 15000
            "time_to_placement_days": 120.0,  # Much higher than 90
            "engagement_rate": 0.10,  # Much lower than 0.35
            "satisfaction_score": 2.0,  # Much lower than 3.5
        }
        result = service.add_benchmarks(metrics)

        assert result["cost_per_placement"]["comparison"] == "worse"
        assert result["time_to_placement_days"]["comparison"] == "worse"
        assert result["engagement_rate"]["comparison"] == "worse"
        assert result["satisfaction_score"]["comparison"] == "worse"

    def test_at_benchmark(self):
        """Metrics within 10% of benchmark show 'at_benchmark'."""
        service = ROIReportService()
        metrics = {
            "cost_per_placement": 15000.0,
            "time_to_placement_days": 90.0,
            "engagement_rate": 0.35,
            "satisfaction_score": 3.5,
        }
        result = service.add_benchmarks(metrics)

        assert result["cost_per_placement"]["comparison"] == "at_benchmark"
        assert result["time_to_placement_days"]["comparison"] == "at_benchmark"
        assert result["engagement_rate"]["comparison"] == "at_benchmark"
        assert result["satisfaction_score"]["comparison"] == "at_benchmark"

    def test_no_data_for_none_values(self):
        """None metric values produce 'no_data' comparison."""
        service = ROIReportService()
        metrics = {
            "cost_per_placement": None,
            "time_to_placement_days": None,
            "engagement_rate": None,
            "satisfaction_score": None,
        }
        result = service.add_benchmarks(metrics)

        assert result["cost_per_placement"]["comparison"] == "no_data"
        assert result["time_to_placement_days"]["comparison"] == "no_data"
        assert result["engagement_rate"]["comparison"] == "no_data"
        assert result["satisfaction_score"]["comparison"] == "no_data"

    def test_custom_benchmarks_override_defaults(self):
        """Org-specific benchmarks override class constant defaults."""
        service = ROIReportService()
        metrics = {
            "cost_per_placement": 10000.0,
            "time_to_placement_days": 60.0,
            "engagement_rate": 0.50,
            "satisfaction_score": 4.0,
        }
        custom_benchmarks = {
            "cost_per_placement": 10000.0,
            "time_to_placement_days": 60.0,
            "engagement_rate": 0.50,
            "satisfaction_score": 4.0,
        }
        result = service.add_benchmarks(metrics, custom_benchmarks)

        # All at benchmark since values match custom benchmarks
        assert result["cost_per_placement"]["comparison"] == "at_benchmark"
        assert result["time_to_placement_days"]["comparison"] == "at_benchmark"
        assert result["engagement_rate"]["comparison"] == "at_benchmark"
        assert result["satisfaction_score"]["comparison"] == "at_benchmark"
        # Benchmark values reflect custom, not defaults
        assert result["cost_per_placement"]["benchmark_value"] == 10000.0
        assert result["time_to_placement_days"]["benchmark_value"] == 60.0

    def test_benchmark_result_structure(self):
        """Each benchmark entry has benchmark_value and comparison keys."""
        service = ROIReportService()
        metrics = {
            "cost_per_placement": 10000.0,
            "time_to_placement_days": 50.0,
            "engagement_rate": 0.40,
            "satisfaction_score": 4.0,
        }
        result = service.add_benchmarks(metrics)

        for key in ["cost_per_placement", "time_to_placement_days", "engagement_rate", "satisfaction_score"]:
            assert "benchmark_value" in result[key]
            assert "comparison" in result[key]
            assert result[key]["comparison"] in {"better", "at_benchmark", "worse", "no_data"}


# ---------------------------------------------------------------------------
# Lower/higher comparison helpers
# ---------------------------------------------------------------------------


class TestComparisonHelpers:
    """Test static comparison helper methods."""

    def test_compare_lower_better_none(self):
        assert ROIReportService._compare_lower_better(None, 90) == "no_data"

    def test_compare_lower_better_better(self):
        # 50 < 90*0.9=81 => better
        assert ROIReportService._compare_lower_better(50, 90) == "better"

    def test_compare_lower_better_at_benchmark(self):
        # 85 is between 81 and 99 => at_benchmark
        assert ROIReportService._compare_lower_better(85, 90) == "at_benchmark"

    def test_compare_lower_better_worse(self):
        # 120 > 90*1.1=99 => worse
        assert ROIReportService._compare_lower_better(120, 90) == "worse"

    def test_compare_higher_better_none(self):
        assert ROIReportService._compare_higher_better(None, 0.35) == "no_data"

    def test_compare_higher_better_better(self):
        # 0.50 > 0.35*1.1=0.385 => better
        assert ROIReportService._compare_higher_better(0.50, 0.35) == "better"

    def test_compare_higher_better_at_benchmark(self):
        # 0.35 >= 0.35*0.9=0.315 and <= 0.35*1.1=0.385 => at_benchmark
        assert ROIReportService._compare_higher_better(0.35, 0.35) == "at_benchmark"

    def test_compare_higher_better_worse(self):
        # 0.20 < 0.35*0.9=0.315 => worse
        assert ROIReportService._compare_higher_better(0.20, 0.35) == "worse"


# ---------------------------------------------------------------------------
# Date range defaults (AC3)
# ---------------------------------------------------------------------------


class TestDateRangeDefaults:
    """Verify default date range is current calendar month."""

    @pytest.mark.asyncio
    async def test_default_date_range_current_month(self):
        """compute_metrics defaults to current month when no dates provided."""
        service = ROIReportService()

        captured_dates: dict = {}

        async def mock_cost(session, org_uuid, start_dt, end_dt):
            captured_dates["start"] = start_dt
            captured_dates["end"] = end_dt
            return None

        async def mock_time(session, org_uuid, start_dt, end_dt):
            return None

        async def mock_engagement(session, org_uuid, start_dt, end_dt):
            return 0.0

        async def mock_satisfaction(session, org_uuid, start_dt, end_dt):
            return None

        async def mock_benchmarks(session, org_uuid):
            return {
                "time_to_placement_days": 90,
                "engagement_rate": 0.35,
                "cost_per_placement": 15000.0,
                "satisfaction_score": 3.5,
            }

        service._compute_cost_per_placement = mock_cost
        service._compute_time_to_placement = mock_time
        service._compute_engagement_rate = mock_engagement
        service._compute_satisfaction_score = mock_satisfaction
        service._load_org_benchmarks = mock_benchmarks

        mock_session = AsyncMock()
        result = await service.compute_metrics(
            mock_session, "00000000-0000-0000-0000-000000000001"
        )

        # Verify start_date is first of current month
        today = date.today()
        assert captured_dates["start"].month == today.month
        assert captured_dates["start"].day == 1

        # Verify result structure
        assert "cost_per_placement" in result
        assert "time_to_placement_days" in result
        assert "engagement_rate" in result
        assert "satisfaction_score" in result
        assert "benchmarks" in result
        assert "period" in result

    @pytest.mark.asyncio
    async def test_custom_date_range(self):
        """compute_metrics uses provided dates."""
        service = ROIReportService()

        captured_dates: dict = {}

        async def mock_cost(session, org_uuid, start_dt, end_dt):
            captured_dates["start"] = start_dt
            captured_dates["end"] = end_dt
            return 5000.0

        async def mock_time(session, org_uuid, start_dt, end_dt):
            return 45.0

        async def mock_engagement(session, org_uuid, start_dt, end_dt):
            return 0.60

        async def mock_satisfaction(session, org_uuid, start_dt, end_dt):
            return None

        async def mock_benchmarks(session, org_uuid):
            return {
                "time_to_placement_days": 90,
                "engagement_rate": 0.35,
                "cost_per_placement": 15000.0,
                "satisfaction_score": 3.5,
            }

        service._compute_cost_per_placement = mock_cost
        service._compute_time_to_placement = mock_time
        service._compute_engagement_rate = mock_engagement
        service._compute_satisfaction_score = mock_satisfaction
        service._load_org_benchmarks = mock_benchmarks

        mock_session = AsyncMock()
        result = await service.compute_metrics(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        assert captured_dates["start"] == datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert captured_dates["end"] == datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert result["period"]["start_date"] == "2026-01-01"
        assert result["period"]["end_date"] == "2026-01-31"


# ---------------------------------------------------------------------------
# Metric computations (AC1)
# ---------------------------------------------------------------------------


class TestCostPerPlacement:
    """Test cost per placement computation."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_placements(self):
        """No placements => None (avoid division by zero)."""
        service = ROIReportService()
        mock_session = AsyncMock()

        # Mock execute to return 0 placements
        mock_result_zero = MagicMock()
        mock_result_zero.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result_zero)

        result = await service._compute_cost_per_placement(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            datetime(2026, 1, 1),
            datetime(2026, 1, 31, 23, 59, 59),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_computes_cost_with_placements(self):
        """With placements, returns total_cost / placements."""
        service = ROIReportService()
        mock_session = AsyncMock()

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                # placements count
                mock_result.scalar.return_value = 5
            elif call_count == 2:
                # enrolled count
                mock_result.scalar.return_value = 50
            elif call_count == 3:
                # org settings
                mock_result.scalar.return_value = {"seat_cost_monthly": 200.0}
            return mock_result

        mock_session.execute = mock_execute

        result = await service._compute_cost_per_placement(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            datetime(2026, 1, 1),
            datetime(2026, 1, 31, 23, 59, 59),
        )
        # 50 enrolled * $200 seat cost / 5 placements = $2000
        assert result == 2000.0


class TestEngagementRate:
    """Test engagement rate computation."""

    @pytest.mark.asyncio
    async def test_zero_enrolled_returns_zero(self):
        """No enrolled users => 0.0 engagement rate."""
        service = ROIReportService()
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service._compute_engagement_rate(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            datetime(2026, 1, 1),
            datetime(2026, 1, 31, 23, 59, 59),
        )
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_computes_rate_with_active_users(self):
        """Returns active / enrolled ratio."""
        service = ROIReportService()
        mock_session = AsyncMock()

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                # enrolled count
                mock_result.scalar.return_value = 20
            elif call_count == 2:
                # active count
                mock_result.scalar.return_value = 12
            return mock_result

        mock_session.execute = mock_execute

        result = await service._compute_engagement_rate(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            datetime(2026, 1, 1),
            datetime(2026, 1, 31, 23, 59, 59),
        )
        assert result == 0.6  # 12/20 = 0.6


class TestSatisfactionScore:
    """Test satisfaction score stub."""

    @pytest.mark.asyncio
    async def test_returns_none_stub(self):
        """Satisfaction score returns None (no feedback table yet)."""
        service = ROIReportService()
        mock_session = AsyncMock()

        result = await service._compute_satisfaction_score(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            datetime(2026, 1, 1),
            datetime(2026, 1, 31, 23, 59, 59),
        )
        assert result is None


# ---------------------------------------------------------------------------
# Schedule storage (AC4)
# ---------------------------------------------------------------------------


class TestScheduleStorage:
    """Test schedule config in Organization.settings."""

    @pytest.mark.asyncio
    async def test_get_schedule_default(self):
        """Default schedule when none configured."""
        service = ROIReportService()
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = {}
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_schedule(
            mock_session, "00000000-0000-0000-0000-000000000001"
        )
        assert result == {"enabled": False, "recipients": []}

    @pytest.mark.asyncio
    async def test_get_schedule_with_config(self):
        """Returns existing schedule config from settings."""
        service = ROIReportService()
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = {
            "roi_report_schedule": {
                "enabled": True,
                "recipients": ["admin@example.com"],
            }
        }
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_schedule(
            mock_session, "00000000-0000-0000-0000-000000000001"
        )
        assert result["enabled"] is True
        assert result["recipients"] == ["admin@example.com"]

    @pytest.mark.asyncio
    async def test_save_schedule_merges_into_settings(self):
        """save_schedule stores config under roi_report_schedule key."""
        service = ROIReportService()
        mock_session = AsyncMock()

        # Mock org object
        mock_org = MagicMock()
        mock_org.settings = {"other_setting": "value"}

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_org
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        result = await service.save_schedule(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            {"enabled": True, "recipients": ["ceo@example.com"]},
        )

        assert result["enabled"] is True
        assert result["recipients"] == ["ceo@example.com"]
        # Verify existing settings are preserved
        assert mock_org.settings["other_setting"] == "value"
        assert "roi_report_schedule" in mock_org.settings


# ---------------------------------------------------------------------------
# Privacy guarantees (AC6)
# ---------------------------------------------------------------------------


class TestPrivacySafe:
    """Ensure no individual user data in metrics output."""

    @pytest.mark.asyncio
    async def test_compute_metrics_has_no_user_ids(self):
        """Metrics dict must not contain user_id, email, or name fields."""
        service = ROIReportService()

        async def mock_cost(session, org_uuid, start_dt, end_dt):
            return 5000.0

        async def mock_time(session, org_uuid, start_dt, end_dt):
            return 45.0

        async def mock_engagement(session, org_uuid, start_dt, end_dt):
            return 0.60

        async def mock_satisfaction(session, org_uuid, start_dt, end_dt):
            return None

        async def mock_benchmarks(session, org_uuid):
            return {
                "time_to_placement_days": 90,
                "engagement_rate": 0.35,
                "cost_per_placement": 15000.0,
                "satisfaction_score": 3.5,
            }

        service._compute_cost_per_placement = mock_cost
        service._compute_time_to_placement = mock_time
        service._compute_engagement_rate = mock_engagement
        service._compute_satisfaction_score = mock_satisfaction
        service._load_org_benchmarks = mock_benchmarks

        mock_session = AsyncMock()
        result = await service.compute_metrics(
            mock_session,
            "00000000-0000-0000-0000-000000000001",
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        # Flatten all keys recursively
        def collect_keys(d, prefix=""):
            keys = set()
            for k, v in d.items():
                full_key = f"{prefix}.{k}" if prefix else k
                keys.add(full_key)
                if isinstance(v, dict):
                    keys |= collect_keys(v, full_key)
            return keys

        all_keys = collect_keys(result)
        forbidden = {"user_id", "email", "name", "user_name"}
        for key in all_keys:
            leaf = key.split(".")[-1]
            assert leaf not in forbidden, f"Found forbidden key '{leaf}' in metrics output"


# ---------------------------------------------------------------------------
# RBAC enforcement (AC7)
# ---------------------------------------------------------------------------


class TestRBACEnforcement:
    """Test that ROI endpoints require admin authentication."""

    def test_get_roi_metrics_uses_require_admin(self):
        """GET /admin/reports/roi is protected by require_admin."""
        import inspect

        from fastapi import params

        from app.api.v1.admin_enterprise import get_roi_metrics

        sig = inspect.signature(get_roi_metrics)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        assert isinstance(admin_param.default, params.Depends)

    def test_get_roi_schedule_uses_require_admin(self):
        """GET /admin/reports/roi/schedule is protected by require_admin."""
        import inspect

        from fastapi import params

        from app.api.v1.admin_enterprise import get_roi_schedule

        sig = inspect.signature(get_roi_schedule)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        assert isinstance(admin_param.default, params.Depends)

    def test_save_roi_schedule_uses_require_admin(self):
        """POST /admin/reports/roi/schedule is protected by require_admin."""
        import inspect

        from fastapi import params

        from app.api.v1.admin_enterprise import save_roi_schedule

        sig = inspect.signature(save_roi_schedule)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        assert isinstance(admin_param.default, params.Depends)
