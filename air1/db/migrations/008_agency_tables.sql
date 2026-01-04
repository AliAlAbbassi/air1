-- Migration: Create agency management tables for admin API

-- Agency table: represents an agency organization
CREATE TABLE IF NOT EXISTS agency (
    agency_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    total_seats INT NOT NULL DEFAULT 5,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

-- Agency member roles
CREATE TYPE agency_role AS ENUM ('owner', 'admin', 'manager');

-- Agency member status
CREATE TYPE member_status AS ENUM ('active', 'pending');

-- Agency members: team members in an agency
CREATE TABLE IF NOT EXISTS agency_member (
    member_id BIGSERIAL PRIMARY KEY,
    agency_id BIGINT NOT NULL REFERENCES agency(agency_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES hodhod_user(user_id) ON DELETE SET NULL,  -- NULL if pending invite
    name VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    role agency_role NOT NULL DEFAULT 'manager',
    status member_status NOT NULL DEFAULT 'pending',
    avatar_url TEXT,
    invited_at TIMESTAMP DEFAULT NOW(),
    joined_at TIMESTAMP,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(agency_id, email)
);

-- Client plan types
CREATE TYPE client_plan AS ENUM ('starter', 'pro', 'enterprise');

-- Client status
CREATE TYPE client_status AS ENUM ('active', 'onboarding');

-- Agency clients: client accounts managed by an agency
CREATE TABLE IF NOT EXISTS agency_client (
    client_id BIGSERIAL PRIMARY KEY,
    agency_id BIGINT NOT NULL REFERENCES agency(agency_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    admin_email VARCHAR(255) NOT NULL,
    status client_status NOT NULL DEFAULT 'onboarding',
    linkedin_connected BOOLEAN DEFAULT FALSE,
    linkedin_profile_url TEXT,
    plan client_plan NOT NULL DEFAULT 'starter',
    last_active TIMESTAMP,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW(),
    
    -- Stats (denormalized for quick access)
    total_campaigns INT DEFAULT 0,
    total_prospects INT DEFAULT 0,
    meetings_booked INT DEFAULT 0,
    
    UNIQUE(agency_id, admin_email)
);

-- Client team members (users within a client account)
CREATE TABLE IF NOT EXISTS client_team_member (
    client_team_member_id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL REFERENCES agency_client(client_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES hodhod_user(user_id) ON DELETE SET NULL,
    name VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    created_on TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(client_id, email)
);

-- Invite tokens for pending invites
CREATE TABLE IF NOT EXISTS agency_invite (
    invite_id BIGSERIAL PRIMARY KEY,
    member_id BIGINT REFERENCES agency_member(member_id) ON DELETE CASCADE,
    client_id BIGINT REFERENCES agency_client(client_id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_on TIMESTAMP DEFAULT NOW(),
    
    CHECK ((member_id IS NOT NULL AND client_id IS NULL) OR (member_id IS NULL AND client_id IS NOT NULL))
);

-- Impersonation tokens for client access
CREATE TABLE IF NOT EXISTS impersonation_token (
    token_id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL REFERENCES agency_client(client_id) ON DELETE CASCADE,
    agency_member_id BIGINT NOT NULL REFERENCES agency_member(member_id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_on TIMESTAMP DEFAULT NOW()
);

-- Link users to agencies (one user can belong to one agency)
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS agency_member_id BIGINT REFERENCES agency_member(member_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agency_member_agency ON agency_member(agency_id);
CREATE INDEX IF NOT EXISTS idx_agency_member_email ON agency_member(email);
CREATE INDEX IF NOT EXISTS idx_agency_member_user ON agency_member(user_id);
CREATE INDEX IF NOT EXISTS idx_agency_member_status ON agency_member(agency_id, status);

CREATE INDEX IF NOT EXISTS idx_agency_client_agency ON agency_client(agency_id);
CREATE INDEX IF NOT EXISTS idx_agency_client_status ON agency_client(agency_id, status);
CREATE INDEX IF NOT EXISTS idx_agency_client_email ON agency_client(admin_email);

CREATE INDEX IF NOT EXISTS idx_client_team_member_client ON client_team_member(client_id);

CREATE INDEX IF NOT EXISTS idx_agency_invite_token ON agency_invite(token);
CREATE INDEX IF NOT EXISTS idx_agency_invite_expires ON agency_invite(expires_at);

CREATE INDEX IF NOT EXISTS idx_impersonation_token ON impersonation_token(token);
CREATE INDEX IF NOT EXISTS idx_impersonation_expires ON impersonation_token(expires_at);

