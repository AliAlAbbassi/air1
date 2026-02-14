-- Migration: Add LinkedIn and Twitter URL columns to sec_company

ALTER TABLE sec_company ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(500);
ALTER TABLE sec_company ADD COLUMN IF NOT EXISTS twitter_url VARCHAR(500);
