-- Migration 00003: Row-Level Security Policies
-- Story 0-2: Data isolation per user via RLS as defense-in-depth
--
-- Uses current_setting('app.current_user_id', true)::uuid for user isolation.
-- The second argument 'true' makes current_setting return NULL instead of
-- raising an error when the setting is not defined.
--
-- Backend sets this per-transaction via: SET LOCAL app.current_user_id = '<uuid>'

-- ============================================================
-- Enable RLS on all 8 user-scoped tables
-- ============================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_outputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE swipe_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE learned_preferences ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- User isolation policies (FOR ALL = SELECT, INSERT, UPDATE, DELETE)
-- ============================================================

CREATE POLICY user_isolation_policy ON profiles
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY user_isolation_policy ON applications
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY user_isolation_policy ON matches
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY user_isolation_policy ON documents
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY user_isolation_policy ON agent_actions
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY user_isolation_policy ON agent_outputs
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY user_isolation_policy ON swipe_events
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY user_isolation_policy ON learned_preferences
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- ============================================================
-- Development bypass policies
-- Requires BOTH app.environment = 'development' AND app.rls_bypass = 'true'
-- ============================================================

CREATE POLICY dev_bypass_policy ON profiles
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');

CREATE POLICY dev_bypass_policy ON applications
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');

CREATE POLICY dev_bypass_policy ON matches
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');

CREATE POLICY dev_bypass_policy ON documents
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');

CREATE POLICY dev_bypass_policy ON agent_actions
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');

CREATE POLICY dev_bypass_policy ON agent_outputs
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');

CREATE POLICY dev_bypass_policy ON swipe_events
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');

CREATE POLICY dev_bypass_policy ON learned_preferences
    FOR ALL
    USING (current_setting('app.environment', true) = 'development' AND current_setting('app.rls_bypass', true) = 'true');
