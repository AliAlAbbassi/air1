-- Migration: Add unique constraint on company name
-- First, remove duplicates (keep the oldest)
DELETE FROM company a USING company b
WHERE a.company_id > b.company_id AND a.name = b.name;

-- Add unique index on name
CREATE UNIQUE INDEX IF NOT EXISTS idx_company_name_unique ON company(name);

