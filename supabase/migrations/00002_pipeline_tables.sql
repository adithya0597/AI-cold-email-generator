-- Migration: 00002_pipeline_tables.sql
-- Description: Create tables for Pipeline Agent email tracking and status changes
-- Date: 2026-02-01

-- ============================================================
-- TABLE: email_connections
-- ============================================================

CREATE TABLE email_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- 'gmail' or 'outlook'
    email_address TEXT NOT NULL,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'disconnected', 'expired'
    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ,
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_email_connections_user_id ON email_connections (user_id);
CREATE INDEX idx_email_connections_provider ON email_connections (provider);
CREATE INDEX idx_email_connections_deleted_at ON email_connections (deleted_at);

CREATE TRIGGER email_connections_updated_at
    BEFORE UPDATE ON email_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: application_status_changes
-- ============================================================

CREATE TABLE application_status_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    old_status application_status,
    new_status application_status NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detection_method TEXT NOT NULL,  -- 'email_parse', 'user_manual', 'agent'
    confidence NUMERIC(5, 2),
    evidence_snippet TEXT,
    source_email_subject TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_app_status_changes_application_id ON application_status_changes (application_id);
CREATE INDEX idx_app_status_changes_detected_at ON application_status_changes (detected_at);
CREATE INDEX idx_app_status_changes_deleted_at ON application_status_changes (deleted_at);
