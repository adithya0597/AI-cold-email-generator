"""agent framework tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-31

Phase 3 schema changes:
- Add columns to agent_outputs: task_id, rationale, confidence
- Create index on agent_outputs (user_id, created_at)
- Create approval_queue table for L2 tier approval workflow
- Create briefings table for daily briefing records
- Create agent_activities table for activity feed persistence
- Add briefing config columns to user_preferences
- Add 'briefing' value to agent_type enum

NOTE: Review when first applied (written manually without DB connection,
consistent with 0002 migration pattern).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Add 'briefing' to agent_type enum ---
    # The agent_type enum already exists in PostgreSQL; add the new value.
    op.execute("ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'briefing'")

    # --- Add columns to agent_outputs ---
    op.add_column(
        "agent_outputs",
        sa.Column("task_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "agent_outputs",
        sa.Column("rationale", sa.Text(), nullable=True),
    )
    op.add_column(
        "agent_outputs",
        sa.Column(
            "confidence",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_agent_outputs_user_created",
        "agent_outputs",
        ["user_id", "created_at"],
    )

    # --- Create approval_queue table ---
    op.create_table(
        "approval_queue",
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
        ),
        sa.Column("agent_type", sa.Text(), nullable=False),
        sa.Column("action_name", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "confidence",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
        ),
        sa.Column("user_decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
    op.create_index(
        "ix_approval_queue_user_status",
        "approval_queue",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_approval_queue_expires",
        "approval_queue",
        ["expires_at"],
    )

    # --- Create briefings table ---
    op.create_table(
        "briefings",
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
        ),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column(
            "briefing_type",
            sa.Text(),
            nullable=False,
            server_default="full",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "delivery_channels",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
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
    )
    op.create_index(
        "ix_briefings_user_generated",
        "briefings",
        ["user_id", "generated_at"],
    )

    # --- Create agent_activities table ---
    op.create_table(
        "agent_activities",
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
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("agent_type", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Text(),
            nullable=False,
            server_default="info",
        ),
        sa.Column(
            "data",
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
    )
    op.create_index(
        "ix_agent_activities_user_created",
        "agent_activities",
        ["user_id", "created_at"],
    )

    # --- Add briefing config columns to user_preferences ---
    op.add_column(
        "user_preferences",
        sa.Column(
            "briefing_hour",
            sa.Integer(),
            nullable=False,
            server_default="8",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "briefing_minute",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "briefing_timezone",
            sa.Text(),
            nullable=False,
            server_default="UTC",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "briefing_channels",
            postgresql.ARRAY(sa.Text()),
            server_default="{in_app,email}",
        ),
    )


def downgrade() -> None:
    # --- Remove briefing config columns from user_preferences ---
    op.drop_column("user_preferences", "briefing_channels")
    op.drop_column("user_preferences", "briefing_timezone")
    op.drop_column("user_preferences", "briefing_minute")
    op.drop_column("user_preferences", "briefing_hour")

    # --- Drop agent_activities table ---
    op.drop_index(
        "ix_agent_activities_user_created",
        table_name="agent_activities",
    )
    op.drop_table("agent_activities")

    # --- Drop briefings table ---
    op.drop_index(
        "ix_briefings_user_generated",
        table_name="briefings",
    )
    op.drop_table("briefings")

    # --- Drop approval_queue table ---
    op.drop_index(
        "ix_approval_queue_expires",
        table_name="approval_queue",
    )
    op.drop_index(
        "ix_approval_queue_user_status",
        table_name="approval_queue",
    )
    op.drop_table("approval_queue")

    # --- Remove columns from agent_outputs ---
    op.drop_index(
        "ix_agent_outputs_user_created",
        table_name="agent_outputs",
    )
    op.drop_column("agent_outputs", "confidence")
    op.drop_column("agent_outputs", "rationale")
    op.drop_column("agent_outputs", "task_id")

    # NOTE: Cannot remove enum value 'briefing' from agent_type in PostgreSQL.
    # Enum values cannot be removed without recreating the type.
    # This is acceptable as the value is harmless if unused.
