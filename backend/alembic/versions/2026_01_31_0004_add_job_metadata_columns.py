"""Add job metadata columns for Phase 4 Job Scout agent.

Adds location, salary_min, salary_max, employment_type, remote,
source_id, raw_data, and posted_at columns to the jobs table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-31

NOTE: Written manually (no DB connection). Review when first applied.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("location", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("salary_min", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("salary_max", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("employment_type", sa.Text(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("remote", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column("jobs", sa.Column("source_id", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("raw_data", JSONB(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "posted_at")
    op.drop_column("jobs", "raw_data")
    op.drop_column("jobs", "source_id")
    op.drop_column("jobs", "remote")
    op.drop_column("jobs", "employment_type")
    op.drop_column("jobs", "salary_max")
    op.drop_column("jobs", "salary_min")
    op.drop_column("jobs", "location")
