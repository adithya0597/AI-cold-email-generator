-- Migration: Set default autonomy config for existing organizations
-- Story: 10-5 Per-Employee Autonomy Configuration
--
-- Sets default autonomy settings in the Organization.settings JSONB
-- for any organizations that do not already have autonomy config.

UPDATE organizations
SET settings = settings || jsonb_build_object(
    'autonomy', jsonb_build_object(
        'default_autonomy', 'l1',
        'max_autonomy', 'l3',
        'restrictions', jsonb_build_object(
            'blocked_companies', '[]'::jsonb,
            'blocked_industries', '[]'::jsonb,
            'require_approval_industries', '[]'::jsonb
        )
    )
)
WHERE settings IS NULL
   OR NOT (settings ? 'autonomy');
