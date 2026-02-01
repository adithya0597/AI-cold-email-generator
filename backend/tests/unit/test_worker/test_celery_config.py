"""
Tests for Story 0.5: Celery configuration with Redis broker.

Validates:
  AC#3 - Celery uses Redis as broker and result backend
  AC#3 - Queue routing for agent tasks
  AC#3 - Reliability settings (acks_late, prefetch, reject_on_worker_lost)
  AC#3 - JSON-only serialization
  AC#3 - RedBeat scheduler configured
"""

from app.config import settings
from app.worker.celery_app import celery_app


# ============================================================
# AC#3 - Celery Broker Connectivity
# ============================================================


class TestBrokerConfiguration:
    """AC#3: Celery connects to Redis as broker and result backend."""

    def test_broker_url_is_redis(self):
        assert celery_app.conf.broker_url == settings.REDIS_URL

    def test_result_backend_is_redis(self):
        assert celery_app.conf.result_backend == settings.REDIS_URL


# ============================================================
# Queue Routing
# ============================================================


class TestQueueRouting:
    """Agent tasks route to specialised queues."""

    def test_task_routes_agents_queue(self):
        routes = celery_app.conf.task_routes
        assert routes["app.worker.tasks.agent_*"] == {"queue": "agents"}

    def test_task_routes_briefings_queue(self):
        routes = celery_app.conf.task_routes
        assert routes["app.worker.tasks.briefing_*"] == {"queue": "briefings"}

    def test_task_routes_scraping_queue(self):
        routes = celery_app.conf.task_routes
        assert routes["app.worker.tasks.scrape_*"] == {"queue": "scraping"}

    def test_task_routes_default_queue(self):
        routes = celery_app.conf.task_routes
        assert routes["app.worker.tasks.*"] == {"queue": "default"}


# ============================================================
# Reliability Settings
# ============================================================


class TestReliabilitySettings:
    """Celery reliability: acks_late, prefetch=1, reject_on_worker_lost."""

    def test_acks_late_enabled(self):
        assert celery_app.conf.task_acks_late is True

    def test_prefetch_multiplier_is_one(self):
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_reject_on_worker_lost(self):
        assert celery_app.conf.task_reject_on_worker_lost is True


# ============================================================
# Serialization
# ============================================================


class TestSerialization:
    """JSON-only serialization for safety."""

    def test_task_serializer_json(self):
        assert celery_app.conf.task_serializer == "json"

    def test_accept_content_json_only(self):
        assert celery_app.conf.accept_content == ["json"]

    def test_result_serializer_json(self):
        assert celery_app.conf.result_serializer == "json"


# ============================================================
# RedBeat Scheduler
# ============================================================


class TestRedBeatScheduler:
    """RedBeat configured for dynamic per-user scheduling."""

    def test_beat_scheduler_is_redbeat(self):
        assert celery_app.conf.beat_scheduler == "redbeat.RedBeatScheduler"

    def test_redbeat_redis_url(self):
        assert celery_app.conf.redbeat_redis_url == settings.REDIS_URL

    def test_redbeat_lock_disabled(self):
        """Single-beat deployment: lock disabled."""
        assert celery_app.conf.redbeat_lock_key is None


# ============================================================
# Timeout Settings (AC#2)
# ============================================================


class TestTimeoutSettings:
    """AC#2: Soft timeout at 240s, hard timeout at 300s."""

    def test_timeout_soft_limit(self):
        assert celery_app.conf.task_soft_time_limit == 240

    def test_timeout_hard_limit(self):
        assert celery_app.conf.task_time_limit == 300


# ============================================================
# Heartbeat / Events (AC#3)
# ============================================================


class TestHeartbeatSettings:
    """AC#3: Worker events enabled for monitoring."""

    def test_worker_events_enabled(self):
        assert celery_app.conf.worker_send_task_events is True

    def test_task_sent_event_enabled(self):
        assert celery_app.conf.task_send_sent_event is True


# ============================================================
# Beat Schedule includes zombie cleanup (AC#6)
# ============================================================


class TestBeatScheduleZombieCleanup:
    """AC#6: beat_schedule includes zombie task cleanup."""

    def test_beat_schedule_has_zombie_cleanup(self):
        import app.worker.tasks  # noqa: F401

        assert "cleanup-zombie-tasks" in celery_app.conf.beat_schedule
