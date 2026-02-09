-- Migration 012: Clean test data from all tables and backfill orphaned companies
--
-- Bug fixes:
-- 1. Migration 011 only cleaned sec_company but left test data in sec_filing, sec_form_d, sec_officer
-- 2. 3 filings parsed before auto-company-creation need their companies retroactively created

-- Step 1: Delete test officers (cascades from test form_d records)
DELETE FROM sec_officer
WHERE sec_form_d_id IN (
    SELECT fd.sec_form_d_id
    FROM sec_form_d fd
    JOIN sec_filing sf ON fd.sec_filing_id = sf.sec_filing_id
    WHERE sf.cik !~ '^[0-9]+$'
);

-- Step 2: Delete test form_d records
DELETE FROM sec_form_d
WHERE sec_filing_id IN (
    SELECT sec_filing_id FROM sec_filing WHERE cik !~ '^[0-9]+$'
);

-- Step 3: Delete test filings
DELETE FROM sec_filing WHERE cik !~ '^[0-9]+$';

-- Step 4: Backfill companies from parsed Form D issuers that were missed
-- (filings parsed before auto-company-creation was added)
INSERT INTO sec_company (cik, name, street, city, state_or_country, phone)
SELECT DISTINCT sf.cik, fd.issuer_name, fd.issuer_street, fd.issuer_city, fd.issuer_state, fd.issuer_phone
FROM sec_filing sf
JOIN sec_form_d fd ON sf.sec_filing_id = fd.sec_filing_id
LEFT JOIN sec_company sc ON sf.cik = sc.cik
WHERE sc.sec_company_id IS NULL
  AND fd.issuer_name IS NOT NULL
ON CONFLICT (cik) DO NOTHING;

-- Step 5: Re-link all orphaned filings
UPDATE sec_filing sf SET
    sec_company_id = sc.sec_company_id
FROM sec_company sc
WHERE sf.cik = sc.cik AND sf.sec_company_id IS NULL;
