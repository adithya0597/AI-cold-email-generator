"""
Celery worker infrastructure for JobPilot.

This package provides the Celery application, task definitions, and queue
routing for background job processing (agents, briefings, scraping, etc.).

Usage:
    celery -A app.worker.celery_app worker --loglevel=info
"""
