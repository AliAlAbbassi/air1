-- Migration 014: LeadGen tables for software userbase discovery
-- Supports multi-tenant lead searches with detection pipeline

-- Catalog of software products with detection fingerprints
CREATE TABLE IF NOT EXISTS software_products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    website TEXT,
    detection_patterns JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- A user's search request (e.g., "find businesses using Cloudbeds in Miami")
CREATE TABLE IF NOT EXISTS lead_searches (
    id SERIAL PRIMARY KEY,
    user_id TEXT,  -- Clerk user ID, nullable for CLI usage
    software_product_id INT NOT NULL REFERENCES software_products(id),
    search_params JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    stats JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Discovered businesses with inline detection status
CREATE TABLE IF NOT EXISTS search_leads (
    id SERIAL PRIMARY KEY,
    lead_search_id INT NOT NULL REFERENCES lead_searches(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    website TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    google_place_id TEXT,
    source TEXT NOT NULL,
    detection_status TEXT NOT NULL DEFAULT 'pending',
    detected_software TEXT,
    detection_method TEXT,
    detection_details JSONB DEFAULT '{}',
    detected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_search_leads_search_id ON search_leads(lead_search_id);
CREATE INDEX IF NOT EXISTS idx_search_leads_detection_status ON search_leads(detection_status);
CREATE INDEX IF NOT EXISTS idx_search_leads_google_place_id ON search_leads(google_place_id);
CREATE INDEX IF NOT EXISTS idx_lead_searches_user_id ON lead_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_lead_searches_status ON lead_searches(status);
