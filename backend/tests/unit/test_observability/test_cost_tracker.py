"""Tests for LLM cost tracking middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.observability.cost_tracker import (
    ALERT_THRESHOLD,
    MODEL_PRICING,
    MONTHLY_BUDGET_USD,
    _DEFAULT_PRICING,
    _KEY_TTL_SECONDS,
    _calculate_cost,
    _month_key,
    get_all_costs_summary,
    get_user_monthly_cost,
    track_llm_cost,
)


# ---------------------------------------------------------------------------
# Cost calculation tests
# ---------------------------------------------------------------------------


class TestCalculateCost:
    """Test USD cost calculation for LLM calls."""

    def test_gpt4o_cost(self):
        """gpt-4o: input=$0.005/1K, output=$0.015/1K."""
        cost = _calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        expected = (1000 / 1000) * 0.005 + (500 / 1000) * 0.015
        assert cost == round(expected, 6)

    def test_claude_3_sonnet_cost(self):
        """claude-3-sonnet: input=$0.003/1K, output=$0.015/1K."""
        cost = _calculate_cost("claude-3-sonnet", input_tokens=2000, output_tokens=1000)
        expected = (2000 / 1000) * 0.003 + (1000 / 1000) * 0.015
        assert cost == round(expected, 6)

    def test_gpt35_turbo_cost(self):
        """gpt-3.5-turbo: cheapest OpenAI model."""
        cost = _calculate_cost("gpt-3.5-turbo", input_tokens=5000, output_tokens=2000)
        expected = (5000 / 1000) * 0.0005 + (2000 / 1000) * 0.0015
        assert cost == round(expected, 6)

    def test_unknown_model_uses_fallback(self):
        """Unknown models use default pricing."""
        cost = _calculate_cost("unknown-model-v42", input_tokens=1000, output_tokens=1000)
        expected = (1000 / 1000) * _DEFAULT_PRICING["input"] + (1000 / 1000) * _DEFAULT_PRICING["output"]
        assert cost == round(expected, 6)

    def test_zero_tokens_returns_zero(self):
        """No tokens means no cost."""
        cost = _calculate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_all_models_have_input_output_pricing(self):
        """Every model in pricing table has both input and output keys."""
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"{model} missing 'input'"
            assert "output" in pricing, f"{model} missing 'output'"


# ---------------------------------------------------------------------------
# Month key tests
# ---------------------------------------------------------------------------


class TestMonthKey:
    """Test Redis key generation."""

    @patch("app.observability.cost_tracker.datetime")
    def test_month_key_format(self, mock_dt):
        """Key format is llm_cost:{user_id}:{YYYY-MM}."""
        from datetime import timezone

        mock_now = MagicMock()
        mock_now.strftime.return_value = "2026-02"
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *a, **kw: MagicMock()

        key = _month_key("user_abc123")
        assert key == "llm_cost:user_abc123:2026-02"


# ---------------------------------------------------------------------------
# track_llm_cost tests
# ---------------------------------------------------------------------------


class TestTrackLlmCost:
    """Test the main cost recording function."""

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    @patch("app.observability.cost_tracker._month_key", return_value="llm_cost:u1:2026-02")
    async def test_records_cost_via_pipeline(self, _mock_key, mock_get_redis):
        """Pipeline increments total_cost, total_input, total_output, calls."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0.01, 100, 50, 1, True]  # results from pipeline
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_get_redis.return_value = mock_redis

        cost = await track_llm_cost("u1", "gpt-4o", 1000, 500)

        assert cost > 0
        mock_pipe.hincrbyfloat.assert_any_call("llm_cost:u1:2026-02", "total_cost", cost)
        mock_pipe.hincrby.assert_any_call("llm_cost:u1:2026-02", "total_input", 1000)
        mock_pipe.hincrby.assert_any_call("llm_cost:u1:2026-02", "total_output", 500)
        mock_pipe.hincrby.assert_any_call("llm_cost:u1:2026-02", "calls", 1)
        mock_pipe.expire.assert_called_once_with("llm_cost:u1:2026-02", _KEY_TTL_SECONDS)

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    @patch("app.observability.cost_tracker._month_key", return_value="llm_cost:u1:2026-02")
    async def test_records_agent_type_when_provided(self, _mock_key, mock_get_redis):
        """When agent_type is given, per-agent counters are incremented."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0.01, 100, 50, 1, 0.01, 1, True]
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_get_redis.return_value = mock_redis

        cost = await track_llm_cost("u1", "gpt-4o", 1000, 500, agent_type="job_scout")

        mock_pipe.hincrbyfloat.assert_any_call("llm_cost:u1:2026-02", "agent:job_scout:cost", cost)
        mock_pipe.hincrby.assert_any_call("llm_cost:u1:2026-02", "agent:job_scout:calls", 1)

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    @patch("app.observability.cost_tracker._month_key", return_value="llm_cost:u1:2026-02")
    async def test_no_agent_fields_when_agent_type_none(self, _mock_key, mock_get_redis):
        """When agent_type is None, no agent: fields are written."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0.01, 100, 50, 1, True]
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_get_redis.return_value = mock_redis

        await track_llm_cost("u1", "gpt-4o", 1000, 500)

        # Check no agent: fields were written
        for call in mock_pipe.hincrbyfloat.call_args_list:
            assert not call[0][1].startswith("agent:"), f"Unexpected agent field: {call}"

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    @patch("app.observability.cost_tracker._month_key", return_value="llm_cost:u1:2026-02")
    async def test_budget_alert_published_at_threshold(self, _mock_key, mock_get_redis):
        """Alert fires when total reaches 80% of $6 budget ($4.80)."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [5.0, 100, 50, 1, True]  # $5.00 > $4.80
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_get_redis.return_value = mock_redis

        await track_llm_cost("u1", "gpt-4o", 1000, 500)

        mock_redis.publish.assert_called_once()
        channel = mock_redis.publish.call_args[0][0]
        assert channel == "alerts:cost:u1"

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    @patch("app.observability.cost_tracker._month_key", return_value="llm_cost:u1:2026-02")
    async def test_no_alert_below_threshold(self, _mock_key, mock_get_redis):
        """No alert when total is below 80% threshold."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [1.0, 100, 50, 1, True]  # $1.00 < $4.80
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_get_redis.return_value = mock_redis

        await track_llm_cost("u1", "gpt-4o", 1000, 500)

        mock_redis.publish.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    async def test_graceful_degradation_on_redis_failure(self, mock_get_redis):
        """Redis failure returns cost without raising."""
        mock_get_redis.side_effect = Exception("Redis down")

        cost = await track_llm_cost("u1", "gpt-4o", 1000, 500)

        # Should still return the calculated cost
        assert cost > 0


# ---------------------------------------------------------------------------
# get_user_monthly_cost tests
# ---------------------------------------------------------------------------


class TestGetUserMonthlyCost:
    """Test per-user cost summary retrieval."""

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    @patch("app.observability.cost_tracker._month_key", return_value="llm_cost:u1:2026-02")
    async def test_returns_summary(self, _mock_key, mock_get_redis):
        """Returns correct summary dict from Redis hash."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            "total_cost": "3.50",
            "total_input": "10000",
            "total_output": "5000",
            "calls": "25",
        }
        mock_get_redis.return_value = mock_redis

        result = await get_user_monthly_cost("u1")

        assert result["user_id"] == "u1"
        assert result["total_cost"] == 3.5
        assert result["total_input_tokens"] == 10000
        assert result["total_output_tokens"] == 5000
        assert result["calls"] == 25
        assert result["budget"] == MONTHLY_BUDGET_USD
        assert result["budget_used_pct"] > 0

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    @patch("app.observability.cost_tracker._month_key", return_value="llm_cost:u1:2026-02")
    async def test_returns_zeros_for_new_user(self, _mock_key, mock_get_redis):
        """New user with no data returns zero-filled summary."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}
        mock_get_redis.return_value = mock_redis

        result = await get_user_monthly_cost("u_new")

        assert result["total_cost"] == 0.0
        assert result["calls"] == 0
        assert result["budget_used_pct"] == 0.0


# ---------------------------------------------------------------------------
# get_all_costs_summary tests
# ---------------------------------------------------------------------------


class TestGetAllCostsSummary:
    """Test aggregate cost summary for admin dashboard."""

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    async def test_aggregates_all_users(self, mock_get_redis):
        """Scans all user keys and aggregates costs."""
        mock_redis = AsyncMock()
        # First scan returns 2 keys, second returns 0 (done)
        mock_redis.scan.side_effect = [
            (0, ["llm_cost:u1:2026-02", "llm_cost:u2:2026-02"]),
        ]
        mock_redis.hgetall.side_effect = [
            {"total_cost": "2.00", "calls": "10", "agent:job_scout:cost": "1.50", "agent:job_scout:calls": "8"},
            {"total_cost": "1.00", "calls": "5", "agent:resume:cost": "1.00", "agent:resume:calls": "5"},
        ]
        mock_get_redis.return_value = mock_redis

        result = await get_all_costs_summary()

        assert result["total_cost_today"] == 3.0
        assert result["total_calls"] == 15
        assert len(result["users"]) == 2
        assert "projected_month_end" in result
        # Per-agent breakdown
        assert "agents" in result
        assert len(result["agents"]) == 2
        agent_names = [a["agent_type"] for a in result["agents"]]
        assert "job_scout" in agent_names
        assert "resume" in agent_names

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    async def test_handles_empty_scan(self, mock_get_redis):
        """Empty scan returns zero totals."""
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [])
        mock_get_redis.return_value = mock_redis

        result = await get_all_costs_summary()

        assert result["total_cost_today"] == 0.0
        assert result["total_calls"] == 0
        assert result["users"] == []
        assert result["agents"] == []

    @pytest.mark.asyncio
    @patch("app.observability.cost_tracker._get_redis")
    async def test_graceful_degradation_on_failure(self, mock_get_redis):
        """Redis failure returns error dict."""
        mock_get_redis.side_effect = Exception("Redis down")

        result = await get_all_costs_summary()

        assert "error" in result


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify budget and threshold constants."""

    def test_monthly_budget(self):
        assert MONTHLY_BUDGET_USD == 6.0

    def test_alert_threshold(self):
        assert ALERT_THRESHOLD == 0.80

    def test_key_ttl_is_35_days(self):
        assert _KEY_TTL_SECONDS == 35 * 24 * 60 * 60
