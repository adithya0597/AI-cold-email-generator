"""phase2 onboarding preferences

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-31

Phase 2 schema changes:
- Add onboarding columns to users table
- Add profile extraction columns to profiles table
- Create user_preferences table with hybrid relational + JSONB schema
- Create indexes for agent querying
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Add onboarding columns to users ---
    op.add_column(
        "users",
        sa.Column(
            "onboarding_status",
            sa.Text(),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "onboarding_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("display_name", sa.Text(), nullable=True),
    )

    # --- Add profile extraction columns to profiles ---
    op.add_column(
        "profiles",
        sa.Column("headline", sa.Text(), nullable=True),
    )
    op.add_column(
        "profiles",
        sa.Column("phone", sa.Text(), nullable=True),
    )
    op.add_column(
        "profiles",
        sa.Column("resume_storage_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "profiles",
        sa.Column("extraction_source", sa.Text(), nullable=True),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "extraction_confidence",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
        ),
    )

    # --- Create user_preferences table ---
    op.create_table(
        "user_preferences",
        # Primary key and foreign key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Job Type Preferences
        sa.Column(
            "job_categories",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "target_titles",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "seniority_levels",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        # Location
        sa.Column("work_arrangement", sa.Text(), nullable=True),
        sa.Column(
            "target_locations",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "excluded_locations",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "willing_to_relocate",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        # Salary
        sa.Column("salary_minimum", sa.Integer(), nullable=True),
        sa.Column("salary_target", sa.Integer(), nullable=True),
        sa.Column("salary_flexibility", sa.Text(), nullable=True),
        sa.Column("comp_preference", sa.Text(), nullable=True),
        # Deal-Breakers
        sa.Column("min_company_size", sa.Integer(), nullable=True),
        sa.Column(
            "excluded_companies",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "excluded_industries",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "must_have_benefits",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column("max_travel_percent", sa.Integer(), nullable=True),
        sa.Column(
            "no_oncall",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        # H1B / Visa
        sa.Column(
            "requires_h1b_sponsorship",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "requires_greencard_sponsorship",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("current_visa_type", sa.Text(), nullable=True),
        sa.Column(
            "visa_expiration",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Autonomy
        sa.Column(
            "autonomy_level",
            sa.Text(),
            nullable=False,
            server_default="l0",
        ),
        # Flexible Extras
        sa.Column(
            "extra_preferences",
            postgresql.JSONB(),
            server_default="{}",
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Soft delete (SoftDeleteMixin)
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deleted_by", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
    )

    # --- Create indexes for efficient agent querying ---
    op.create_index(
        "ix_user_preferences_user_id",
        "user_preferences",
        ["user_id"],
    )
    op.create_index(
        "ix_user_preferences_h1b",
        "user_preferences",
        ["requires_h1b_sponsorship"],
    )
    op.create_index(
        "ix_user_preferences_autonomy",
        "user_preferences",
        ["autonomy_level"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_user_preferences_autonomy", table_name="user_preferences")
    op.drop_index("ix_user_preferences_h1b", table_name="user_preferences")
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")

    # Drop user_preferences table
    op.drop_table("user_preferences")

    # Remove profile extraction columns
    op.drop_column("profiles", "extraction_confidence")
    op.drop_column("profiles", "extraction_source")
    op.drop_column("profiles", "resume_storage_path")
    op.drop_column("profiles", "phone")
    op.drop_column("profiles", "headline")

    # Remove onboarding columns from users
    op.drop_column("users", "display_name")
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "onboarding_started_at")
    op.drop_column("users", "onboarding_status")
