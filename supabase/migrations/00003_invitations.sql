-- Migration: 00003_invitations.sql
-- Description: Employee invitation flow — invitation records with token-based accept/decline
-- Depends on: 00002_enterprise_admin.sql (organizations, organization_members, audit_logs)
-- Date: 2026-02-02

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'declined', 'expired', 'revoked');

-- ============================================================
-- TABLE: invitations
-- ============================================================

CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    status invitation_status NOT NULL DEFAULT 'pending',
    invited_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_org_email_status ON invitations(org_id, email, status);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;

-- Admins can read their org's invitations
CREATE POLICY invitations_admin_select ON invitations FOR SELECT
    USING (org_id IN (
        SELECT om.org_id FROM organization_members om
        WHERE om.user_id = current_setting('app.current_user_id')::uuid
        AND om.role = 'admin'
    ));

-- Admins can insert invitations for their org
CREATE POLICY invitations_admin_insert ON invitations FOR INSERT
    WITH CHECK (org_id IN (
        SELECT om.org_id FROM organization_members om
        WHERE om.user_id = current_setting('app.current_user_id')::uuid
        AND om.role = 'admin'
    ));

-- Admins can update invitations for their org (revoke, etc.)
CREATE POLICY invitations_admin_update ON invitations FOR UPDATE
    USING (org_id IN (
        SELECT om.org_id FROM organization_members om
        WHERE om.user_id = current_setting('app.current_user_id')::uuid
        AND om.role = 'admin'
    ));

-- Service role bypass for token-based accept/decline (public endpoints)
-- The application backend uses service role to update invitation status
-- when users accept/decline via token (no Clerk JWT required).
CREATE POLICY invitations_service_role ON invitations FOR ALL
    USING (current_setting('role', true) = 'service_role');
