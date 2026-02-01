-- Migration: Cleanup invalid contact points created by 422 bug
-- Date: 2026-01-31
-- Issue: Contact points were incorrectly created when connection requests failed
--        with 422 errors but were treated as successful
--
-- Background:
-- Between 2026-01-31 20:00 and 23:00, a bug caused all LinkedIn connection
-- requests to fail with 422 errors due to invalid profile ID format.
-- The bug incorrectly treated these failures as successes and created
-- contact_point records in the database.
--
-- Impact:
-- - Users have contact points but no actual LinkedIn connection was made
-- - Future runs will skip these users thinking they're already contacted
-- - Database shows false positives for outreach attempts

-- Step 1: Identify affected contact points
-- (Run this first to review before deletion)
SELECT
    cp.contact_point_id,
    lp.username,
    lp.name,
    cp.created_on,
    cp.lead_id,
    'Invalid - connection failed with 422' as status
FROM contact_point cp
JOIN linkedin_profile lp ON lp.lead_id = cp.lead_id
WHERE cp.contact_point_type_id = 1  -- LinkedIn connection type
  AND cp.created_on >= '2026-01-31 20:00:00'
  AND cp.created_on <= '2026-01-31 23:00:00'
ORDER BY cp.created_on DESC;

-- Step 2: Delete the invalid contact points
-- IMPORTANT: Review the SELECT results above before running this DELETE
DELETE FROM contact_point
WHERE contact_point_id IN (
    SELECT cp.contact_point_id
    FROM contact_point cp
    WHERE cp.contact_point_type_id = 1
      AND cp.created_on >= '2026-01-31 20:00:00'
      AND cp.created_on <= '2026-01-31 23:00:00'
);

-- Step 3: Verify deletion
-- This should return 0 rows after deletion
SELECT
    COUNT(*) as remaining_invalid_contact_points,
    'Should be 0 after successful cleanup' as note
FROM contact_point cp
WHERE cp.contact_point_type_id = 1
  AND cp.created_on >= '2026-01-31 20:00:00'
  AND cp.created_on <= '2026-01-31 23:00:00';

-- Expected result: 0 rows (all invalid contact points removed)

-- After running this migration:
-- 1. Affected profiles will be retried in future connection request runs
-- 2. The bug has been fixed to properly detect invalid 422 responses
-- 3. Only legitimate "already connected" 422 responses will create contact points
