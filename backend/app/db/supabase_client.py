"""
Supabase SDK client for JobPilot.

Use ONLY for:
  - File storage (Supabase Storage: resume uploads, signed URLs)
  - Auth token forwarding (Supabase Auth, if needed alongside Clerk)
  - Realtime subscriptions (Supabase Realtime)

ALL application data access (users, jobs, applications, matches, documents,
agent actions, agent outputs) MUST use SQLAlchemy via engine.py / session.py.

See ADR-2 (backend/docs/adr/002-database-access-pattern.md) for rationale.
"""

import os

from supabase import Client, create_client


def get_supabase_client() -> Client:
    """Create and return a Supabase client instance."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
        )

    return create_client(url, key)


# Module-level client for convenience (lazy initialization)
_client: Client | None = None


def get_client() -> Client:
    """Get or create the singleton Supabase client."""
    global _client
    if _client is None:
        _client = get_supabase_client()
    return _client
