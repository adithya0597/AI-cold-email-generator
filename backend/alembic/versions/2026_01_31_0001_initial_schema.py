"""initial schema baseline

Revision ID: 0001
Revises:
Create Date: 2026-01-31

BASELINE MIGRATION -- DO NOT RUN.

Tables were created via Supabase migration supabase/migrations/00001_initial_schema.sql.
This Alembic migration represents the same schema for autogenerate diffing purposes.
It was stamped as applied via `alembic stamp head` (not executed against the database).

All future schema changes MUST go through Alembic, not raw SQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types
    # NOTE: create_type=False on the ORM models means these enums are managed
    # at the database level. They already exist in Supabase.
    user_tier = postgresql.ENUM(
        "free", "pro", "h1b_pro", "career_insurance", "enterprise",
        name="user_tier", create_type=False,
    )
    application_status = postgresql.ENUM(
        "applied", "screening", "interview", "offer", "closed", "rejected",
        name="application_status", create_type=False,
    )
    match_status = postgresql.ENUM(
        "new", "saved", "dismissed", "applied",
        name="match_status", create_type=False,
    )
    document_type = postgresql.ENUM(
        "resume", "cover_letter",
        name="document_type", create_type=False,
    )
    agent_type = postgresql.ENUM(
        "orchestrator", "job_scout", "resume", "apply", "pipeline",
        "follow_up", "interview_intel", "network",
        name="agent_type", create_type=False,
    )
    h1b_sponsor_status = postgresql.ENUM(
        "verified", "unverified", "unknown",
        name="h1b_sponsor_status", create_type=False,
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("clerk_id", sa.Text(), nullable=False, unique=True),
        sa.Column("tier", user_tier, nullable=False, server_default="free"),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- profiles ---
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linkedin_data", postgresql.JSONB(), nullable=True),
        sa.Column("skills", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("experience", postgresql.ARRAY(postgresql.JSONB()), nullable=True),
        sa.Column("education", postgresql.ARRAY(postgresql.JSONB()), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
    )

    # --- jobs ---
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("h1b_sponsor_status", h1b_sponsor_status, nullable=False,
                   server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- applications ---
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", application_status, nullable=False,
                   server_default="applied"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resume_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
    )

    # --- matches ---
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", match_status, nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", document_type, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
    )

    # --- agent_actions ---
    op.create_table(
        "agent_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_type", agent_type, nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
    )

    # --- agent_outputs ---
    op.create_table(
        "agent_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type", agent_type, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("output", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_outputs")
    op.drop_table("agent_actions")
    op.drop_table("documents")
    op.drop_table("matches")
    op.drop_table("applications")
    op.drop_table("jobs")
    op.drop_table("profiles")
    op.drop_table("users")
