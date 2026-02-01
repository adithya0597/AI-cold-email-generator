"""
Celery application configuration for JobPilot.

Creates the Celery app with Redis as broker/backend, reliability settings,
queue routing for different agent types, and sensible defaults for
serialization, timeouts, and retries.

IMPORTANT: This module must NOT import from app.db or app.main at module
level.  Celery workers run in their own process and importing async
SQLAlchemy or FastAPI at import time causes event-loop conflicts.
Settings are imported from app.config which is safe (pydantic-settings,
no async machinery).
"""

import asyncio
import logging

from celery import Celery
from celery.signals import task_failure

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------

celery_app = Celery("jobpilot")

celery_app.conf.update(
    # --- Broker / Backend (Redis) ---
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,

    # --- Serialization: JSON-only for safety ---
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    event_serializer="json",

    # --- Reliability ---
    # Workers acknowledge *after* task completes, not before.  If the
    # worker crashes mid-task the message returns to the queue.
    task_acks_late=True,
    # Fetch one task at a time so work is distributed fairly across workers
    # and a long-running task doesn't block others queued behind it.
    worker_prefetch_multiplier=1,
    # If the worker process is killed (OOM, SIGKILL) while executing a task,
    # reject the message so it is redelivered rather than silently lost.
    task_reject_on_worker_lost=True,

    # --- Timeouts ---
    # Soft limit raises SoftTimeLimitExceeded inside the task so it can
    # clean up.  Hard limit kills the worker process after an additional 60s.
    task_soft_time_limit=240,
    task_time_limit=300,

    # --- Result expiry ---
    result_expires=3600,  # 1 hour

    # --- Heartbeat / Events ---
    worker_send_task_events=True,
    task_send_sent_event=True,

    # --- Queue routing ---
    # Tasks are routed to specialised queues by naming convention.  Workers
    # can be started on specific queues, e.g.:
    #   celery -A app.worker.celery_app worker -Q agents --concurrency=2
    task_routes={
        "app.worker.tasks.agent_*": {"queue": "agents"},
        "app.worker.tasks.briefing_*": {"queue": "briefings"},
        "app.worker.tasks.scrape_*": {"queue": "scraping"},
        "app.worker.tasks.*": {"queue": "default"},
    },

    # --- Retry defaults ---
    # Tasks that call self.retry() without arguments use these defaults.
    task_default_retry_delay=30,  # seconds
    task_max_retries=3,

    # --- Misc ---
    timezone="UTC",
    enable_utc=True,

    # --- RedBeat (dynamic per-user scheduling) ---
    # Use RedBeat as the beat scheduler for dynamic schedule management.
    # Schedules are stored in Redis and can be added/removed without restart.
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.REDIS_URL,
    redbeat_key_prefix="redbeat:",
    redbeat_lock_key=None,  # Disable lock for single-beat deployments
)

# Auto-discover tasks in the worker package.
celery_app.autodiscover_tasks(["app.worker"])


# ---------------------------------------------------------------------------
# Dead-letter queue signal handler
# ---------------------------------------------------------------------------


@task_failure.connect
def _on_task_failure(sender=None, task_id=None, args=None, kwargs=None,
                     exception=None, **kw):
    """Push failed tasks to the dead letter queue in Redis.

    This signal fires after a task raises an unhandled exception (including
    after all retries are exhausted).  The handler is synchronous (Celery
    signals run in the worker thread) so we use ``asyncio.run()`` to call
    the async DLQ writer.
    """
    from app.worker.dlq import handle_task_failure

    task_name = sender.name if sender else "unknown"
    try:
        asyncio.run(
            handle_task_failure(
                task_id=task_id or "unknown",
                task_name=task_name,
                args=args or (),
                kwargs=kwargs or {},
                exc=exception or "unknown error",
                queue="default",
            )
        )
    except Exception:
        logger.exception("Failed to write task %s to DLQ", task_id)
