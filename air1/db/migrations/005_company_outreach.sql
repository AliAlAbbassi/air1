-- Migration: Add company outreach tracking
-- Track companies found from job searches and whether we've reached out to their employees

-- Add source column to track where company came from
ALTER TABLE company ADD COLUMN IF NOT EXISTS source VARCHAR(50);
-- source values: 'job_search', 'manual', 'scrape', etc.

-- Add job_geo_id to track which geo location the job search was for
ALTER TABLE company ADD COLUMN IF NOT EXISTS job_geo_id VARCHAR(50);

-- Track outreach status per company
CREATE TABLE IF NOT EXISTS company_outreach (
    company_outreach_id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES company(company_id) ON DELETE CASCADE,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'skipped'
    employees_contacted INT DEFAULT 0,               -- count of employees we've connected with
    
    -- Notes and metadata
    notes TEXT,
    
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(company_id)
);

-- Index for quick status lookups
CREATE INDEX IF NOT EXISTS idx_company_outreach_status ON company_outreach(status);

