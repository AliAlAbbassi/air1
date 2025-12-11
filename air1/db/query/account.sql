-- name: get_account_by_user_id^
-- Get full account data for a user
SELECT
    u.user_id,
    u.email,
    u.first_name,
    u.last_name,
    u.timezone,
    u.meeting_link,
    u.linkedin_connected,
    c.company_id,
    c.name AS company_name,
    c.linkedin_username AS company_linkedin_username
FROM hodhod_user u
LEFT JOIN company c ON c.user_id = u.user_id
WHERE u.user_id = :user_id;

-- name: update_user_profile!
-- Update user profile fields (only non-null values)
UPDATE hodhod_user
SET
    first_name = COALESCE(:first_name, first_name),
    last_name = COALESCE(:last_name, last_name),
    timezone = COALESCE(:timezone, timezone),
    meeting_link = COALESCE(:meeting_link, meeting_link),
    updated_on = NOW()
WHERE user_id = :user_id;
