"""
Pub/sub utilities for agent control channels.

Provides channel templates and helpers for publishing/subscribing
to agent control events (pause, resume, status updates).
"""

from app.cache.redis_client import get_redis_client

# Channel templates — substitute {user_id} before use
AGENT_PAUSE_CHANNEL = "agent:pause:{user_id}"
AGENT_RESUME_CHANNEL = "agent:resume:{user_id}"
AGENT_STATUS_CHANNEL = "agent:status:{user_id}"


def format_channel(template: str, user_id: str) -> str:
    """Substitute user_id into a channel template."""
    return template.format(user_id=user_id)


async def publish_control_event(
    channel_template: str, user_id: str, data: str
) -> int:
    """Publish a message to a formatted agent control channel.

    Returns the number of subscribers that received the message.
    """
    channel = format_channel(channel_template, user_id)
    client = await get_redis_client()
    return await client.publish(channel, data)


async def subscribe_control_channel(channel_template: str, user_id: str):
    """Subscribe to a formatted agent control channel.

    Returns a redis.client.PubSub object already subscribed to the channel.
    Caller is responsible for iterating messages and unsubscribing.
    """
    channel = format_channel(channel_template, user_id)
    client = await get_redis_client()
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub
