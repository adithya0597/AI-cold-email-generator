"""
Database layer for JobPilot.

- engine.py: SQLAlchemy async engine + session factory (PRIMARY data access)
- session.py: FastAPI dependency for DB session injection
- models.py: ORM model definitions
- supabase_client.py: Supabase SDK client (storage/auth ONLY)
"""

from app.db.engine import AsyncSessionLocal, engine
from app.db.session import get_db

__all__ = ["engine", "AsyncSessionLocal", "get_db"]
