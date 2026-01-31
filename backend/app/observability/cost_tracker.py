"""
LLM cost tracking middleware.

Tracks per-user LLM API spend using Redis-backed monthly aggregation.
Each call to ``track_llm_cost`` increments the user's monthly counters and
checks whether the user has exceeded 80 % of their budget ($6/month default).

Redis key schema::

    llm_cost:{user_id}:{YYYY-MM}  ->  Hash {
        total_cost:       "0.0342"
        total_input:      "12450"
        total_output:     "3210"
        calls:            "17"
    }

Keys auto-expire after 35 days so old months are cleaned up automatically.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model pricing table  (USD per 1 000 tokens)
# ---------------------------------------------------------------------------

MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Anthropic
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-haiku": {"input": 0.001, "output": 0.005},
}

# Fallback pricing when the model name is not in the table.
_DEFAULT_PRICING: Dict[str, float] = {"input": 0.01, "output": 0.03}

# Monthly budget threshold (USD).  An alert is published when a user exceeds
# this fraction of the budget.
MONTHLY_BUDGET_USD: float = 6.0
ALERT_THRESHOLD: float = 0.80  # 80 %

# Redis key TTL -- 35 days covers a full billing month plus overlap.
_KEY_TTL_SECONDS: int = 35 * 24 * 60 * 60


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_redis() -> aioredis.Redis:
    """Return a Redis client from the configured URL."""
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _month_key(user_id: str) -> str:
    """Return the Redis key for the current calendar month."""
    now = datetime.now(timezone.utc)
    return f"llm_cost:{user_id}:{now.strftime('%Y-%m')}"


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a single LLM call."""
    pricing = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    cost = (input_tokens / 1_000) * pricing["input"] + (output_tokens / 1_000) * pricing["output"]
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def track_llm_cost(
    user_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Record an LLM API call's cost and return the incremental USD amount.

    Parameters
    ----------
    user_id:
        The Clerk user id (``user_...``).
    model:
        Model identifier (e.g. ``gpt-4-turbo``, ``claude-3-sonnet``).
    input_tokens:
        Number of prompt / input tokens consumed.
    output_tokens:
        Number of completion / output tokens consumed.

    Returns
    -------
    float
        The cost in USD for this single call.
    """
    cost = _calculate_cost(model, input_tokens, output_tokens)
    key = _month_key(user_id)

    try:
        r = _get_redis()
        async with r.pipeline(transaction=True) as pipe:
            pipe.hincrbyfloat(key, "total_cost", cost)
            pipe.hincrby(key, "total_input", input_tokens)
            pipe.hincrby(key, "total_output", output_tokens)
            pipe.hincrby(key, "calls", 1)
            pipe.expire(key, _KEY_TTL_SECONDS)
            results = await pipe.execute()

        new_total = float(results[0])

        # Budget alert
        if new_total >= MONTHLY_BUDGET_USD * ALERT_THRESHOLD:
            alert_channel = f"alerts:cost:{user_id}"
            await r.publish(
                alert_channel,
                f"User {user_id} has reached ${new_total:.2f} "
                f"({new_total / MONTHLY_BUDGET_USD * 100:.0f}% of "
                f"${MONTHLY_BUDGET_USD:.2f} budget)",
            )
            logger.warning(
                "LLM cost alert: user=%s total=$%.2f budget=$%.2f",
                user_id,
                new_total,
                MONTHLY_BUDGET_USD,
            )

        await r.aclose()
    except Exception:
        # Cost tracking should never break the hot path -- log and move on.
        logger.exception("Failed to record LLM cost (user=%s, model=%s)", user_id, model)

    return cost


async def get_user_monthly_cost(user_id: str) -> Dict[str, Any]:
    """Return the cost summary for *user_id* in the current month."""
    key = _month_key(user_id)
    try:
        r = _get_redis()
        data = await r.hgetall(key)
        await r.aclose()
        if not data:
            return {
                "user_id": user_id,
                "month": datetime.now(timezone.utc).strftime("%Y-%m"),
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "calls": 0,
                "budget": MONTHLY_BUDGET_USD,
                "budget_used_pct": 0.0,
            }
        total_cost = float(data.get("total_cost", 0))
        return {
            "user_id": user_id,
            "month": datetime.now(timezone.utc).strftime("%Y-%m"),
            "total_cost": round(total_cost, 4),
            "total_input_tokens": int(data.get("total_input", 0)),
            "total_output_tokens": int(data.get("total_output", 0)),
            "calls": int(data.get("calls", 0)),
            "budget": MONTHLY_BUDGET_USD,
            "budget_used_pct": round(total_cost / MONTHLY_BUDGET_USD * 100, 1),
        }
    except Exception:
        logger.exception("Failed to read LLM cost data for user=%s", user_id)
        return {"user_id": user_id, "error": "Cost data unavailable"}


async def get_all_costs_summary() -> Dict[str, Any]:
    """Return an aggregate cost summary across all users for the current month.

    Scans Redis for ``llm_cost:*:YYYY-MM`` keys and sums them up.
    Intended for the admin dashboard endpoint.
    """
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    pattern = f"llm_cost:*:{month}"
    users: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_calls = 0

    try:
        r = _get_redis()
        cursor: int = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                data = await r.hgetall(key)
                # Extract user_id from key  (llm_cost:{user_id}:{YYYY-MM})
                parts = key.rsplit(":", 1)
                uid = parts[0].replace("llm_cost:", "", 1) if len(parts) == 2 else "unknown"
                user_cost = float(data.get("total_cost", 0))
                user_calls = int(data.get("calls", 0))
                total_cost += user_cost
                total_calls += user_calls
                users.append({
                    "user_id": uid,
                    "total_cost": round(user_cost, 4),
                    "calls": user_calls,
                })
            if cursor == 0:
                break
        await r.aclose()
    except Exception:
        logger.exception("Failed to aggregate LLM cost data")
        return {"month": month, "error": "Cost data unavailable"}

    # Simple linear projection for month-end cost
    now = datetime.now(timezone.utc)
    day_of_month = now.day
    days_in_month = 30  # approximation
    projected = total_cost / max(day_of_month, 1) * days_in_month

    return {
        "month": month,
        "total_cost_today": round(total_cost, 4),
        "total_calls": total_calls,
        "projected_month_end": round(projected, 2),
        "users": sorted(users, key=lambda u: u["total_cost"], reverse=True),
    }
