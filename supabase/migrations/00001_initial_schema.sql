-- Migration: 00001_initial_schema.sql
-- Description: Create all foundational tables for JobPilot
-- Date: 2026-01-30

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE user_tier AS ENUM (
    'free', 'pro', 'h1b_pro', 'career_insurance', 'enterprise'
);

CREATE TYPE application_status AS ENUM (
    'applied', 'screening', 'interview', 'offer', 'closed', 'rejected'
);

CREATE TYPE match_status AS ENUM (
    'new', 'saved', 'dismissed', 'applied'
);

CREATE TYPE document_type AS ENUM (
    'resume', 'cover_letter'
);

CREATE TYPE agent_type AS ENUM (
    'orchestrator', 'job_scout', 'resume', 'apply',
    'pipeline', 'follow_up', 'interview_intel', 'network'
);

CREATE TYPE h1b_sponsor_status AS ENUM (
    'verified', 'unverified', 'unknown'
);

-- ============================================================
-- HELPER FUNCTION: auto-update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TABLE: users
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    clerk_id TEXT NOT NULL UNIQUE,
    tier user_tier NOT NULL DEFAULT 'free',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_clerk_id ON users (clerk_id);
CREATE INDEX idx_users_email ON users (email);

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: profiles
-- ============================================================

CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    linkedin_data JSONB,
    skills TEXT[] DEFAULT '{}',
    experience JSONB[] DEFAULT '{}',
    education JSONB[] DEFAULT '{}',
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE UNIQUE INDEX idx_profiles_user_id ON profiles (user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_profiles_deleted_at ON profiles (deleted_at);

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: jobs
-- ============================================================

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    url TEXT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    description TEXT,
    h1b_sponsor_status h1b_sponsor_status NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jobs_company ON jobs (company);
CREATE INDEX idx_jobs_h1b_sponsor_status ON jobs (h1b_sponsor_status);

CREATE TRIGGER jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: applications
-- ============================================================

CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status application_status NOT NULL DEFAULT 'applied',
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resume_version_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_applications_user_id ON applications (user_id);
CREATE INDEX idx_applications_job_id ON applications (job_id);
CREATE INDEX idx_applications_status ON applications (status);
CREATE INDEX idx_applications_deleted_at ON applications (deleted_at);

CREATE TRIGGER applications_updated_at
    BEFORE UPDATE ON applications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: matches
-- ============================================================

CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    score NUMERIC(5, 2),
    rationale TEXT,
    status match_status NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_matches_user_id ON matches (user_id);
CREATE INDEX idx_matches_job_id ON matches (job_id);
CREATE INDEX idx_matches_status ON matches (status);
CREATE INDEX idx_matches_deleted_at ON matches (deleted_at);

CREATE TRIGGER matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: documents
-- ============================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type document_type NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_documents_user_id ON documents (user_id);
CREATE INDEX idx_documents_job_id ON documents (job_id);
CREATE INDEX idx_documents_type ON documents (type);
CREATE INDEX idx_documents_deleted_at ON documents (deleted_at);

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: agent_actions
-- ============================================================

CREATE TABLE agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_type agent_type NOT NULL,
    action TEXT NOT NULL,
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_agent_actions_user_id ON agent_actions (user_id);
CREATE INDEX idx_agent_actions_agent_type ON agent_actions (agent_type);
CREATE INDEX idx_agent_actions_status ON agent_actions (status);
CREATE INDEX idx_agent_actions_deleted_at ON agent_actions (deleted_at);

CREATE TRIGGER agent_actions_updated_at
    BEFORE UPDATE ON agent_actions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: agent_outputs
-- ============================================================

CREATE TABLE agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type agent_type NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    schema_version INTEGER NOT NULL DEFAULT 1,
    output JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_outputs_user_id ON agent_outputs (user_id);
CREATE INDEX idx_agent_outputs_agent_type ON agent_outputs (agent_type);

CREATE TRIGGER agent_outputs_updated_at
    BEFORE UPDATE ON agent_outputs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
