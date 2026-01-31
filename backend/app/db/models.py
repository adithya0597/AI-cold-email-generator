"""
SQLAlchemy ORM models for JobPilot database schema.

These models mirror the Supabase PostgreSQL schema defined in
supabase/migrations/00001_initial_schema.sql.
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ============================================================
# Enum definitions
# ============================================================


class UserTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    H1B_PRO = "h1b_pro"
    CAREER_INSURANCE = "career_insurance"
    ENTERPRISE = "enterprise"


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    CLOSED = "closed"
    REJECTED = "rejected"


class MatchStatus(str, enum.Enum):
    NEW = "new"
    SAVED = "saved"
    DISMISSED = "dismissed"
    APPLIED = "applied"


class DocumentType(str, enum.Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"


class AgentType(str, enum.Enum):
    ORCHESTRATOR = "orchestrator"
    JOB_SCOUT = "job_scout"
    RESUME = "resume"
    APPLY = "apply"
    PIPELINE = "pipeline"
    FOLLOW_UP = "follow_up"
    INTERVIEW_INTEL = "interview_intel"
    NETWORK = "network"
    BRIEFING = "briefing"


# ============================================================
# Text constant classes (not PG Enum -- Phase 2 convention)
# Used for columns stored as Text to avoid ALTER TYPE migrations
# ============================================================


class ApprovalStatus:
    """Status values for approval_queue items. Stored as Text columns."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PAUSED = "paused"


class BrakeState:
    """Brake state values. Stored as Text columns / Redis hashes."""
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    PARTIAL = "partial"
    RESUMING = "resuming"


class ActivitySeverity:
    """Severity levels for agent activity feed. Stored as Text columns."""
    INFO = "info"
    WARNING = "warning"
    ACTION_REQUIRED = "action_required"


class BriefingType:
    """Briefing type values. Stored as Text columns."""
    FULL = "full"
    LITE = "lite"


class H1BSponsorStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class OnboardingStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PROFILE_PENDING = "profile_pending"
    PROFILE_COMPLETE = "profile_complete"
    PREFERENCES_PENDING = "preferences_pending"
    COMPLETE = "complete"


class WorkArrangement(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    OPEN = "open"


class AutonomyLevel(str, enum.Enum):
    L0_SUGGESTIONS = "l0"
    L1_DRAFTS = "l1"
    L2_SUPERVISED = "l2"
    L3_AUTONOMOUS = "l3"


# ============================================================
# Mixin for soft delete columns
# ============================================================


class SoftDeleteMixin:
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    deletion_reason = Column(Text, nullable=True)


# ============================================================
# Mixin for timestamp columns
# ============================================================


class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


# ============================================================
# Table models
# ============================================================


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(Text, nullable=False, unique=True)
    clerk_id = Column(Text, nullable=False, unique=True)
    tier = Column(
        Enum(UserTier, name="user_tier", create_type=False),
        nullable=False,
        default=UserTier.FREE,
    )
    timezone = Column(Text, nullable=False, default="UTC")

    # Onboarding fields
    onboarding_status = Column(
        Text, nullable=False, server_default="not_started"
    )
    onboarding_started_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    display_name = Column(Text, nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)
    preferences = relationship(
        "UserPreference", back_populates="user", uselist=False
    )
    applications = relationship("Application", back_populates="user")
    matches = relationship("Match", back_populates="user")
    documents = relationship("Document", back_populates="user")
    agent_actions = relationship("AgentAction", back_populates="user")
    agent_outputs = relationship("AgentOutput", back_populates="user")


class Profile(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    linkedin_data = Column(JSONB, nullable=True)
    skills = Column(ARRAY(Text), default=[])
    experience = Column(ARRAY(JSONB), default=[])
    education = Column(ARRAY(JSONB), default=[])
    schema_version = Column(Integer, nullable=False, default=1)

    # Phase 2: profile extraction fields
    headline = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    resume_storage_path = Column(Text, nullable=True)
    extraction_source = Column(Text, nullable=True)  # 'resume' | 'linkedin' | 'manual'
    extraction_confidence = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00

    # Relationships
    user = relationship("User", back_populates="profile")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    company = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    h1b_sponsor_status = Column(
        Enum(H1BSponsorStatus, name="h1b_sponsor_status", create_type=False),
        nullable=False,
        default=H1BSponsorStatus.UNKNOWN,
    )

    # Relationships
    applications = relationship("Application", back_populates="job")
    matches = relationship("Match", back_populates="job")
    documents = relationship("Document", back_populates="job")


class Application(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(
        Enum(ApplicationStatus, name="application_status", create_type=False),
        nullable=False,
        default=ApplicationStatus.APPLIED,
    )
    applied_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    resume_version_id = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")


class Match(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(Numeric(5, 2), nullable=True)
    rationale = Column(Text, nullable=True)
    status = Column(
        Enum(MatchStatus, name="match_status", create_type=False),
        nullable=False,
        default=MatchStatus.NEW,
    )

    # Relationships
    user = relationship("User", back_populates="matches")
    job = relationship("Job", back_populates="matches")


class Document(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(
        Enum(DocumentType, name="document_type", create_type=False), nullable=False
    )
    version = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=False)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    schema_version = Column(Integer, nullable=False, default=1)

    # Relationships
    user = relationship("User", back_populates="documents")
    job = relationship("Job", back_populates="documents")


class AgentAction(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "agent_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    agent_type = Column(
        Enum(AgentType, name="agent_type", create_type=False), nullable=False
    )
    action = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="agent_actions")


class AgentOutput(TimestampMixin, Base):
    __tablename__ = "agent_outputs"
    __table_args__ = (
        Index("ix_agent_outputs_user_created", "user_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_type = Column(
        Enum(AgentType, name="agent_type", create_type=False), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_id = Column(Text, nullable=True)  # Celery task ID
    output = Column(JSONB, nullable=False)
    rationale = Column(Text, nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)
    schema_version = Column(Integer, nullable=False, default=1)

    # Relationships
    user = relationship("User", back_populates="agent_outputs")


class ApprovalQueueItem(SoftDeleteMixin, TimestampMixin, Base):
    """Pending agent actions awaiting L2 user approval."""

    __tablename__ = "approval_queue"
    __table_args__ = (
        Index("ix_approval_queue_user_status", "user_id", "status"),
        Index("ix_approval_queue_expires", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_type = Column(Text, nullable=False)
    action_name = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)  # Serialized action context
    status = Column(Text, nullable=False, server_default="pending")
    rationale = Column(Text, nullable=True)  # Agent's rationale for the action
    confidence = Column(Numeric(3, 2), nullable=True)
    user_decision_reason = Column(Text, nullable=True)  # Why user approved/rejected
    decided_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    user = relationship("User", backref="approval_items")


class Briefing(TimestampMixin, Base):
    """Daily briefing records."""

    __tablename__ = "briefings"
    __table_args__ = (
        Index("ix_briefings_user_generated", "user_id", "generated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(JSONB, nullable=False)  # Structured briefing data
    briefing_type = Column(Text, nullable=False, server_default="full")  # "full" | "lite"
    generated_at = Column(DateTime(timezone=True), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    delivery_channels = Column(ARRAY(Text), server_default="{}")  # ["in_app", "email"]
    read_at = Column(DateTime(timezone=True), nullable=True)
    schema_version = Column(Integer, nullable=False, default=1)

    # Relationships
    user = relationship("User", backref="briefings")


class AgentActivity(TimestampMixin, Base):
    """Agent activity feed persistence for real-time and historical display."""

    __tablename__ = "agent_activities"
    __table_args__ = (
        Index("ix_agent_activities_user_created", "user_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(Text, nullable=False)
    agent_type = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    severity = Column(Text, nullable=False, server_default="info")  # info | warning | action_required
    data = Column(JSONB, server_default="{}")
    # Note: created_at comes from TimestampMixin

    # Relationships
    user = relationship("User", backref="agent_activities")


class UserPreference(SoftDeleteMixin, TimestampMixin, Base):
    """User job preferences and deal-breakers.

    Uses a hybrid schema: relational columns for frequently-queried
    deal-breaker fields (efficient agent filtering) plus JSONB for
    flexible/evolving preferences.
    """

    __tablename__ = "user_preferences"
    __table_args__ = (
        Index("ix_user_preferences_user_id", "user_id"),
        Index("ix_user_preferences_h1b", "requires_h1b_sponsorship"),
        Index("ix_user_preferences_autonomy", "autonomy_level"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # --- Job Type Preferences ---
    job_categories = Column(ARRAY(Text), server_default="{}")
    target_titles = Column(ARRAY(Text), server_default="{}")
    seniority_levels = Column(ARRAY(Text), server_default="{}")

    # --- Location ---
    work_arrangement = Column(Text, nullable=True)
    target_locations = Column(ARRAY(Text), server_default="{}")
    excluded_locations = Column(ARRAY(Text), server_default="{}")
    willing_to_relocate = Column(Boolean, nullable=False, server_default="false")

    # --- Salary ---
    salary_minimum = Column(Integer, nullable=True)
    salary_target = Column(Integer, nullable=True)
    salary_flexibility = Column(Text, nullable=True)  # "firm" | "negotiable"
    comp_preference = Column(Text, nullable=True)  # "base_only" | "total_comp"

    # --- Deal-Breakers ---
    min_company_size = Column(Integer, nullable=True)
    excluded_companies = Column(ARRAY(Text), server_default="{}")
    excluded_industries = Column(ARRAY(Text), server_default="{}")
    must_have_benefits = Column(ARRAY(Text), server_default="{}")
    max_travel_percent = Column(Integer, nullable=True)
    no_oncall = Column(Boolean, nullable=False, server_default="false")

    # --- H1B / Visa ---
    requires_h1b_sponsorship = Column(
        Boolean, nullable=False, server_default="false"
    )
    requires_greencard_sponsorship = Column(
        Boolean, nullable=False, server_default="false"
    )
    current_visa_type = Column(Text, nullable=True)
    visa_expiration = Column(DateTime(timezone=True), nullable=True)

    # --- Autonomy ---
    autonomy_level = Column(Text, nullable=False, server_default="l0")

    # --- Flexible Extras (JSONB for evolving preferences) ---
    extra_preferences = Column(JSONB, server_default="{}")

    # --- Briefing Configuration ---
    briefing_hour = Column(Integer, nullable=False, server_default="8")  # 0-23, UTC
    briefing_minute = Column(Integer, nullable=False, server_default="0")
    briefing_timezone = Column(Text, nullable=False, server_default="UTC")
    briefing_channels = Column(
        ARRAY(Text), server_default="{in_app,email}"
    )  # ["in_app", "email"]

    # Relationships
    user = relationship("User", back_populates="preferences")
