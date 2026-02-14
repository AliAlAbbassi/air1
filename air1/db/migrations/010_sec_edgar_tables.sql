-- Migration: Create SEC EDGAR tables for company ingestion pipeline

CREATE TABLE IF NOT EXISTS sec_company (
    sec_company_id BIGSERIAL PRIMARY KEY,
    cik VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    ticker VARCHAR(20),
    exchange VARCHAR(20),
    sic VARCHAR(10),
    sic_description VARCHAR(500),
    state_of_incorp VARCHAR(50),
    fiscal_year_end VARCHAR(4),
    street VARCHAR(500),
    city VARCHAR(255),
    state_or_country VARCHAR(50),
    zip_code VARCHAR(20),
    phone VARCHAR(50),
    website VARCHAR(500),
    enriched_at TIMESTAMP,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sec_company_sic ON sec_company(sic);

CREATE TABLE IF NOT EXISTS sec_filing (
    sec_filing_id BIGSERIAL PRIMARY KEY,
    accession_number VARCHAR(25) UNIQUE NOT NULL,
    cik VARCHAR(10) NOT NULL,
    form_type VARCHAR(20) NOT NULL,
    filing_date DATE NOT NULL,
    company_name VARCHAR(500),
    sec_company_id BIGINT REFERENCES sec_company(sec_company_id) ON DELETE SET NULL,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sec_filing_cik ON sec_filing(cik);
CREATE INDEX IF NOT EXISTS idx_sec_filing_form_type ON sec_filing(form_type);
CREATE INDEX IF NOT EXISTS idx_sec_filing_date ON sec_filing(filing_date);

CREATE TABLE IF NOT EXISTS sec_form_d (
    sec_form_d_id BIGSERIAL PRIMARY KEY,
    sec_filing_id BIGINT UNIQUE NOT NULL REFERENCES sec_filing(sec_filing_id) ON DELETE CASCADE,
    issuer_name VARCHAR(500),
    issuer_street VARCHAR(500),
    issuer_city VARCHAR(255),
    issuer_state VARCHAR(50),
    issuer_zip VARCHAR(20),
    issuer_phone VARCHAR(50),
    entity_type VARCHAR(100),
    industry_group_type VARCHAR(100),
    revenue_range VARCHAR(100),
    federal_exemptions VARCHAR(500),
    total_offering_amount DECIMAL(20, 2),
    total_amount_sold DECIMAL(20, 2),
    total_remaining DECIMAL(20, 2),
    date_of_first_sale DATE,
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sec_officer (
    sec_officer_id BIGSERIAL PRIMARY KEY,
    sec_form_d_id BIGINT NOT NULL REFERENCES sec_form_d(sec_form_d_id) ON DELETE CASCADE,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    title VARCHAR(500),
    street VARCHAR(500),
    city VARCHAR(255),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    created_on TIMESTAMP DEFAULT NOW(),
    updated_on TIMESTAMP DEFAULT NOW()
);
