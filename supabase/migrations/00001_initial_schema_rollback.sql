-- Rollback: 00001_initial_schema.sql
-- Description: Drop all foundational tables for JobPilot
-- Date: 2026-01-30

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS agent_outputs CASCADE;
DROP TABLE IF EXISTS agent_actions CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop the trigger function
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop enum types
DROP TYPE IF EXISTS h1b_sponsor_status;
DROP TYPE IF EXISTS agent_type;
DROP TYPE IF EXISTS document_type;
DROP TYPE IF EXISTS match_status;
DROP TYPE IF EXISTS application_status;
DROP TYPE IF EXISTS user_tier;
