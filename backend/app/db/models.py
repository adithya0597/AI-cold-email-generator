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
    Column,
    DateTime,
    Enum,
    ForeignKey,
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


class H1BSponsorStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


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

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_type = Column(
        Enum(AgentType, name="agent_type", create_type=False), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    schema_version = Column(Integer, nullable=False, default=1)
    output = Column(JSONB, nullable=False)

    # Relationships
    user = relationship("User", back_populates="agent_outputs")
