-- Migration: 00002_swipe_events_learned_preferences
-- Story 4-9: Preference Learning from Swipe Behavior
--
-- Creates swipe_events table (append-only event log) and
-- learned_preferences table (soft-deletable preference patterns).

-- ============================================================
-- Enum: learned_preference_status
-- ============================================================

CREATE TYPE learned_preference_status AS ENUM ('pending', 'acknowledged', 'rejected');

-- ============================================================
-- Table: swipe_events
-- ============================================================

CREATE TABLE swipe_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    action TEXT NOT NULL,  -- 'saved' | 'dismissed'
    job_company TEXT,
    job_location TEXT,
    job_remote BOOLEAN,
    job_salary_min INTEGER,
    job_salary_max INTEGER,
    job_employment_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_swipe_events_user_id ON swipe_events(user_id);

-- ============================================================
-- Table: learned_preferences
-- ============================================================

CREATE TABLE learned_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL,
    pattern_value TEXT NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.0,
    occurrences INTEGER NOT NULL DEFAULT 0,
    status learned_preference_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX ix_learned_preferences_user_id ON learned_preferences(user_id);
CREATE INDEX ix_learned_preferences_status ON learned_preferences(status);

-- ============================================================
-- Triggers: updated_at auto-update
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_swipe_events_updated_at
    BEFORE UPDATE ON swipe_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_learned_preferences_updated_at
    BEFORE UPDATE ON learned_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
