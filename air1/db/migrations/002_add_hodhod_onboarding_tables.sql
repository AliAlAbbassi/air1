-- Migration: Add Hodhod Onboarding Tables
-- Description: Creates tables for user onboarding flow

-- ============================================================================
-- HODHOD USER TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS hodhod_user (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    password_hash TEXT,
    auth_method VARCHAR(50) NOT NULL,
    timezone VARCHAR(50),
    meeting_link TEXT,
    linkedin_connected BOOLEAN DEFAULT FALSE,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hodhod_user_email ON hodhod_user(email);

-- ============================================================================
-- HODHOD COMPANY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS hodhod_company (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES hodhod_user(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    website VARCHAR(255),
    industry VARCHAR(255),
    linkedin_url TEXT,
    employee_count VARCHAR(50),
    logo TEXT,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hodhod_company_user ON hodhod_company(user_id);

-- ============================================================================
-- HODHOD PRODUCT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS hodhod_product (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES hodhod_user(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL REFERENCES hodhod_company(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url TEXT,
    description TEXT,
    ideal_customer_profile TEXT,
    competitors TEXT,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hodhod_product_user ON hodhod_product(user_id);
CREATE INDEX IF NOT EXISTS idx_hodhod_product_company ON hodhod_product(company_id);

-- ============================================================================
-- HODHOD WRITING STYLE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS hodhod_writing_style (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES hodhod_user(id) ON DELETE CASCADE,
    selected_template VARCHAR(255),
    dos TEXT[] DEFAULT '{}',
    donts TEXT[] DEFAULT '{}',
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hodhod_writing_style_user ON hodhod_writing_style(user_id);
