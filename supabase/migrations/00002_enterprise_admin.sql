-- Migration: 00002_enterprise_admin.sql
-- Description: Enterprise admin role, organizations, membership, audit logging, and RLS policies
-- Date: 2026-02-02

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE org_role AS ENUM ('admin', 'member');

-- ============================================================
-- TABLE: organizations
-- ============================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    logo_url TEXT,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete columns
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES users(id),
    deletion_reason TEXT
);

CREATE TRIGGER organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: organization_members
-- ============================================================

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role org_role NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

CREATE TRIGGER organization_members_updated_at
    BEFORE UPDATE ON organization_members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: audit_logs
-- ============================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id UUID,
    changes JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- ALTER TABLE: users — add org_id for quick org lookup
-- ============================================================

ALTER TABLE users ADD COLUMN org_id UUID REFERENCES organizations(id);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_org_members_org_id ON organization_members(org_id);
CREATE INDEX idx_org_members_user_id ON organization_members(user_id);
CREATE INDEX idx_audit_logs_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX idx_users_org_id ON users(org_id);

-- ============================================================
-- ROW LEVEL SECURITY: enable
-- ============================================================

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- RLS POLICIES
-- ============================================================

-- organizations: members can SELECT their org
CREATE POLICY org_member_select ON organizations FOR SELECT
    USING (id IN (
        SELECT om.org_id FROM organization_members om
        WHERE om.user_id = current_setting('app.current_user_id')::uuid
    ));

-- organization_members: members can SELECT same-org members
CREATE POLICY org_members_select ON organization_members FOR SELECT
    USING (org_id IN (
        SELECT om.org_id FROM organization_members om
        WHERE om.user_id = current_setting('app.current_user_id')::uuid
    ));

-- organization_members: admins can INSERT/UPDATE/DELETE
CREATE POLICY org_members_admin_write ON organization_members FOR ALL
    USING (org_id IN (
        SELECT om.org_id FROM organization_members om
        WHERE om.user_id = current_setting('app.current_user_id')::uuid
        AND om.role = 'admin'
    ));

-- audit_logs: admins can SELECT their org's logs
CREATE POLICY audit_logs_admin_select ON audit_logs FOR SELECT
    USING (org_id IN (
        SELECT om.org_id FROM organization_members om
        WHERE om.user_id = current_setting('app.current_user_id')::uuid
        AND om.role = 'admin'
    ));
