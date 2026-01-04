-- ============================================================================
-- ADMIN API QUERIES
-- ============================================================================

-- ============================================================================
-- AGENCY & MEMBER QUERIES
-- ============================================================================

-- name: get_agency_by_member_user_id^
-- Get agency details for a user
SELECT
    a.agency_id,
    a.name,
    a.total_seats,
    a.created_on,
    am.member_id,
    am.role,
    am.status
FROM agency a
JOIN agency_member am ON am.agency_id = a.agency_id
WHERE am.user_id = :user_id
  AND am.status = 'active';

-- name: get_agency_members
-- Get all members in an agency
SELECT
    am.member_id,
    am.name,
    am.email,
    am.role::TEXT AS role,
    am.status::TEXT AS status,
    am.avatar_url,
    am.invited_at,
    am.joined_at,
    am.user_id
FROM agency_member am
WHERE am.agency_id = :agency_id
ORDER BY 
    CASE am.role 
        WHEN 'owner' THEN 1 
        WHEN 'admin' THEN 2 
        ELSE 3 
    END,
    am.joined_at NULLS LAST;

-- name: get_agency_used_seats$
-- Count active/pending members in agency
SELECT COUNT(*)::INT AS used_seats
FROM agency_member
WHERE agency_id = :agency_id
  AND status IN ('active', 'pending');

-- name: get_member_by_id^
-- Get a specific member by ID
SELECT
    am.member_id,
    am.agency_id,
    am.user_id,
    am.name,
    am.email,
    am.role::TEXT AS role,
    am.status::TEXT AS status,
    am.avatar_url,
    am.invited_at,
    am.joined_at
FROM agency_member am
WHERE am.member_id = :member_id;

-- name: get_member_by_email^
-- Get a member by email within an agency
SELECT
    am.member_id,
    am.agency_id,
    am.name,
    am.email,
    am.role::TEXT AS role,
    am.status::TEXT AS status,
    am.avatar_url,
    am.invited_at,
    am.joined_at
FROM agency_member am
WHERE am.agency_id = :agency_id
  AND am.email = :email;

-- name: insert_agency_member^
-- Insert a new agency member (for invites)
INSERT INTO agency_member (agency_id, email, role, status, invited_at)
VALUES (:agency_id, :email, :role::agency_role, 'pending', NOW())
RETURNING member_id, email, role::TEXT AS role, status::TEXT AS status, invited_at;

-- name: update_member_role^
-- Update a member's role
UPDATE agency_member
SET role = :role::agency_role,
    updated_on = NOW()
WHERE member_id = :member_id
RETURNING member_id, role::TEXT AS role, updated_on;

-- name: delete_member!
-- Delete a member from agency
DELETE FROM agency_member
WHERE member_id = :member_id;

-- name: update_member_joined!
-- Update member status when they accept invite
UPDATE agency_member
SET status = 'active',
    user_id = :user_id,
    name = :name,
    joined_at = NOW(),
    updated_on = NOW()
WHERE member_id = :member_id;

-- ============================================================================
-- INVITE QUERIES
-- ============================================================================

-- name: create_invite^
-- Create an invite token
INSERT INTO agency_invite (member_id, client_id, token, expires_at)
VALUES (:member_id, :client_id, :token, :expires_at::TIMESTAMP)
RETURNING invite_id, token, expires_at;

-- name: get_invite_by_token^
-- Get invite details by token
SELECT
    ai.invite_id,
    ai.member_id,
    ai.client_id,
    ai.token,
    ai.expires_at,
    ai.created_on
FROM agency_invite ai
WHERE ai.token = :token
  AND ai.expires_at > NOW();

-- name: delete_invite!
-- Delete an invite (consumed or expired)
DELETE FROM agency_invite
WHERE invite_id = :invite_id;

-- name: delete_invites_by_member!
-- Delete all invites for a member
DELETE FROM agency_invite
WHERE member_id = :member_id;

-- ============================================================================
-- CLIENT QUERIES
-- ============================================================================

-- name: get_agency_clients
-- Get all clients for an agency
SELECT
    ac.client_id,
    ac.name,
    ac.admin_email,
    ac.status::TEXT AS status,
    ac.linkedin_connected,
    ac.plan::TEXT AS plan,
    ac.last_active,
    ac.created_on,
    ac.total_campaigns,
    ac.total_prospects,
    ac.meetings_booked
FROM agency_client ac
WHERE ac.agency_id = :agency_id
ORDER BY ac.created_on DESC;

-- name: get_agency_clients_filtered
-- Get clients filtered by status and search
SELECT
    ac.client_id,
    ac.name,
    ac.admin_email,
    ac.status::TEXT AS status,
    ac.linkedin_connected,
    ac.plan::TEXT AS plan,
    ac.last_active,
    ac.created_on,
    ac.total_campaigns,
    ac.total_prospects,
    ac.meetings_booked
FROM agency_client ac
WHERE ac.agency_id = :agency_id
  AND (:status IS NULL OR ac.status::TEXT = :status)
  AND (:search IS NULL OR ac.name ILIKE '%' || :search || '%' OR ac.admin_email ILIKE '%' || :search || '%')
ORDER BY ac.created_on DESC;

-- name: count_agency_clients$
-- Count clients matching filter
SELECT COUNT(*)::INT
FROM agency_client ac
WHERE ac.agency_id = :agency_id
  AND (:status IS NULL OR ac.status::TEXT = :status)
  AND (:search IS NULL OR ac.name ILIKE '%' || :search || '%' OR ac.admin_email ILIKE '%' || :search || '%');

-- name: get_client_by_id^
-- Get a specific client by ID
SELECT
    ac.client_id,
    ac.agency_id,
    ac.name,
    ac.admin_email,
    ac.status::TEXT AS status,
    ac.linkedin_connected,
    ac.linkedin_profile_url,
    ac.plan::TEXT AS plan,
    ac.last_active,
    ac.created_on,
    ac.total_campaigns,
    ac.total_prospects,
    ac.meetings_booked
FROM agency_client ac
WHERE ac.client_id = :client_id;

-- name: insert_client^
-- Create a new client
INSERT INTO agency_client (agency_id, name, admin_email, plan, status)
VALUES (:agency_id, :name, :admin_email, :plan::client_plan, 'onboarding')
RETURNING client_id, name, admin_email, status::TEXT AS status, linkedin_connected, plan::TEXT AS plan, created_on;

-- name: update_client^
-- Update client details
UPDATE agency_client
SET name = COALESCE(:name, name),
    plan = COALESCE(:plan::client_plan, plan),
    updated_on = NOW()
WHERE client_id = :client_id
RETURNING client_id, name, admin_email, status::TEXT AS status, linkedin_connected, plan::TEXT AS plan, last_active, created_on, total_campaigns, total_prospects, meetings_booked;

-- name: delete_client!
-- Delete a client
DELETE FROM agency_client
WHERE client_id = :client_id;

-- name: update_client_linkedin!
-- Update client's linkedin connection status
UPDATE agency_client
SET linkedin_connected = :linkedin_connected,
    linkedin_profile_url = :linkedin_profile_url,
    status = CASE WHEN :linkedin_connected THEN 'active'::client_status ELSE status END,
    updated_on = NOW()
WHERE client_id = :client_id;

-- ============================================================================
-- CLIENT TEAM QUERIES
-- ============================================================================

-- name: get_client_team
-- Get team members for a client
SELECT
    ctm.client_team_member_id,
    ctm.name,
    ctm.email,
    ctm.role
FROM client_team_member ctm
WHERE ctm.client_id = :client_id
ORDER BY ctm.created_on;

-- ============================================================================
-- IMPERSONATION QUERIES
-- ============================================================================

-- name: create_impersonation_token^
-- Create an impersonation token
INSERT INTO impersonation_token (client_id, agency_member_id, token, expires_at)
VALUES (:client_id, :member_id, :token, :expires_at::TIMESTAMP)
RETURNING token_id, token, expires_at;

-- name: get_impersonation_token^
-- Validate an impersonation token
SELECT
    it.token_id,
    it.client_id,
    it.agency_member_id,
    it.expires_at,
    ac.name AS client_name
FROM impersonation_token it
JOIN agency_client ac ON ac.client_id = it.client_id
WHERE it.token = :token
  AND it.expires_at > NOW();

-- name: delete_impersonation_token!
-- Delete an impersonation token (after use)
DELETE FROM impersonation_token
WHERE token_id = :token_id;

