"""
WebSocket endpoint for real-time agent status updates.

Clients connect at ``/api/v1/ws/agents/{user_id}`` and receive JSON
messages whenever the backend publishes events to the Redis pub/sub
channel ``agent:status:{user_id}``.

Authentication is performed via a ``token`` query parameter containing
a valid Clerk JWT.  If no token is provided the connection is rejected
with WebSocket close code 4401.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)


async def _get_redis():
    """Lazily create an async Redis client."""
    import redis.asyncio as aioredis
    from app.config import settings

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def publish_agent_event(user_id: str, event: Dict[str, Any]) -> None:
    """
    Publish an agent event to Redis pub/sub.

    Call this from Celery workers or API endpoints to push real-time
    updates to connected WebSocket clients.

    Args:
        user_id: The Clerk user ID that owns the agent session.
        event: JSON-serializable dict with at least a ``type`` key.
    """
    try:
        client = await _get_redis()
        channel = f"agent:status:{user_id}"
        await client.publish(channel, json.dumps(event))
        await client.aclose()
    except Exception as exc:
        logger.warning("Failed to publish agent event: %s", exc)


@router.websocket("/ws/agents/{user_id}")
async def agent_websocket(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(default=""),
):
    """
    WebSocket endpoint for agent status streaming.

    Connects to Redis pub/sub channel ``agent:status:{user_id}`` and
    forwards every published message to the WebSocket client.

    Query Parameters:
        token: Clerk JWT for authentication (required).
    """
    # --- Authentication -----------------------------------------------
    if not token:
        await websocket.close(code=4401, reason="Authentication required")
        return

    from app.auth.ws_auth import validate_ws_token
    from app.config import settings

    validated_user = await validate_ws_token(token)
    if validated_user is None and settings.CLERK_DOMAIN:
        # In production with CLERK_DOMAIN set, reject invalid tokens
        await websocket.close(code=4401, reason="Invalid or expired token")
        return
    # In dev without CLERK_DOMAIN, fall through with the URL user_id

    await websocket.accept()
    logger.info("WebSocket connected for user %s", user_id)

    try:
        client = await _get_redis()
        pubsub = client.pubsub()
        channel = f"agent:status:{user_id}"
        await pubsub.subscribe(channel)

        # Listen for messages from Redis and forward to WebSocket
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])

            # Also check for incoming client messages (ping/pong, close)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=0.1
                )
                # Client can send a JSON ping; echo back as pong
                if data:
                    try:
                        parsed = json.loads(data)
                        if parsed.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                    except json.JSONDecodeError:
                        pass
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for user %s", user_id)
    except Exception as exc:
        logger.error("WebSocket error for user %s: %s", user_id, exc)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await client.aclose()
        except Exception:
            pass
