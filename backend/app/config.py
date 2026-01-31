"""
Centralized application configuration using pydantic-settings.

All environment variables are loaded here and accessed via the `settings` singleton.
Add new config values as fields on the Settings class -- they will be automatically
loaded from environment variables (case-insensitive) or .env files.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_ENV: str = "development"
    APP_NAME: str = "JobPilot"
    DEBUG: bool = False

    # --- Database (PostgreSQL via SQLAlchemy async + asyncpg) ---
    # Use direct connection (port 5432), NOT PgBouncer (port 6543)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobpilot"

    # --- Supabase (storage and auth token forwarding ONLY) ---
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # --- Redis (Celery broker + cache) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Authentication (Clerk) ---
    CLERK_DOMAIN: str = ""

    # --- LLM API Keys ---
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # --- Observability ---
    SENTRY_DSN: str = ""

    # --- Langfuse (LLM observability -- replaces cost_tracker.py) ---
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"

    # --- Email (Resend) ---
    RESEND_API_KEY: str = ""

    # --- Analytics (PostHog) ---
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://us.i.posthog.com"

    # --- Job Board Aggregator APIs ---
    RAPIDAPI_KEY: str = ""
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    INDEED_RAPIDAPI_HOST: str = ""  # e.g. "indeed-scraper.p.rapidapi.com"
    LINKEDIN_RAPIDAPI_HOST: str = ""  # e.g. "linkedin-jobs-scraper-api1.p.rapidapi.com"

    # --- Job Matching ---
    MATCH_SCORE_THRESHOLD: int = 40
    LLM_SCORING_ENABLED: bool = True

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"


settings = Settings()
