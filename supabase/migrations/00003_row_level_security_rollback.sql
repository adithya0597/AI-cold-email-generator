-- Rollback Migration 00003: Remove Row-Level Security Policies
-- Drops all 16 policies (user_isolation + dev_bypass per table)
-- then disables RLS on all 8 user-scoped tables.

-- ============================================================
-- Drop user isolation policies
-- ============================================================

DROP POLICY IF EXISTS user_isolation_policy ON profiles;
DROP POLICY IF EXISTS user_isolation_policy ON applications;
DROP POLICY IF EXISTS user_isolation_policy ON matches;
DROP POLICY IF EXISTS user_isolation_policy ON documents;
DROP POLICY IF EXISTS user_isolation_policy ON agent_actions;
DROP POLICY IF EXISTS user_isolation_policy ON agent_outputs;
DROP POLICY IF EXISTS user_isolation_policy ON swipe_events;
DROP POLICY IF EXISTS user_isolation_policy ON learned_preferences;

-- ============================================================
-- Drop development bypass policies
-- ============================================================

DROP POLICY IF EXISTS dev_bypass_policy ON profiles;
DROP POLICY IF EXISTS dev_bypass_policy ON applications;
DROP POLICY IF EXISTS dev_bypass_policy ON matches;
DROP POLICY IF EXISTS dev_bypass_policy ON documents;
DROP POLICY IF EXISTS dev_bypass_policy ON agent_actions;
DROP POLICY IF EXISTS dev_bypass_policy ON agent_outputs;
DROP POLICY IF EXISTS dev_bypass_policy ON swipe_events;
DROP POLICY IF EXISTS dev_bypass_policy ON learned_preferences;

-- ============================================================
-- Disable RLS on all 8 user-scoped tables
-- ============================================================

ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE applications DISABLE ROW LEVEL SECURITY;
ALTER TABLE matches DISABLE ROW LEVEL SECURITY;
ALTER TABLE documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions DISABLE ROW LEVEL SECURITY;
ALTER TABLE agent_outputs DISABLE ROW LEVEL SECURITY;
ALTER TABLE swipe_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE learned_preferences DISABLE ROW LEVEL SECURITY;
