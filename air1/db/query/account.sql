-- name: get_user_by_email^
-- Get user by email for authentication
SELECT
    user_id,
    email,
    password_hash,
    auth_method
FROM hodhod_user
WHERE email = :email;

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

-- name: get_account_by_clerk_id^
-- Get full account data for a user by Clerk ID
SELECT
    u.user_id,
    u.clerk_id,
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
WHERE u.clerk_id = :clerk_id;

-- name: create_user_from_clerk^
-- Create a new user from Clerk authentication
INSERT INTO hodhod_user (clerk_id, email, auth_method, created_on, updated_on)
VALUES (:clerk_id, :email, 'clerk', NOW(), NOW())
RETURNING user_id, clerk_id, email, first_name, last_name, timezone, meeting_link, linkedin_connected;

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

-- name: update_user_profile_by_clerk_id!
-- Update user profile fields by Clerk ID
UPDATE hodhod_user
SET
    first_name = COALESCE(:first_name, first_name),
    last_name = COALESCE(:last_name, last_name),
    timezone = COALESCE(:timezone, timezone),
    meeting_link = COALESCE(:meeting_link, meeting_link),
    updated_on = NOW()
WHERE clerk_id = :clerk_id;
