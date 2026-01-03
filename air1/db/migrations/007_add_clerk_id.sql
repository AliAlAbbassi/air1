-- Migration: Add clerk_id column for Clerk authentication

ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS clerk_id VARCHAR(255) UNIQUE;

CREATE INDEX IF NOT EXISTS idx_hodhod_user_clerk_id ON hodhod_user(clerk_id);

