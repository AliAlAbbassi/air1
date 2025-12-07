-- Migration: Add onboarding columns to existing tables
-- Description: Extends hodhod_user, company, product, and writing_style tables for onboarding flow

-- ============================================================================
-- HODHOD_USER TABLE EXTENSIONS
-- ============================================================================

ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS auth_method VARCHAR(50);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS first_name VARCHAR(255);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS last_name VARCHAR(255);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS timezone VARCHAR(50);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS meeting_link TEXT;
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS linkedin_connected BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- COMPANY TABLE EXTENSIONS
-- ============================================================================

ALTER TABLE company ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE company ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES hodhod_user(user_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_company_user ON company(user_id);

-- Note: company.linkedin_username already has UNIQUE constraint in schema.sql
-- This supports ON CONFLICT (linkedin_username) in onboarding queries

-- ============================================================================
-- PRODUCT TABLE EXTENSIONS
-- ============================================================================

ALTER TABLE product ADD COLUMN IF NOT EXISTS competitors TEXT;

-- ============================================================================
-- WRITING STYLE TABLE EXTENSIONS
-- ============================================================================

ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS dos TEXT[];
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS donts TEXT[];
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS selected_template VARCHAR(255);
