-- name: upsert_sec_company^
INSERT INTO sec_company (cik, name, ticker, exchange)
VALUES (:cik, :name, :ticker, :exchange)
ON CONFLICT (cik) DO UPDATE SET
    name = COALESCE(EXCLUDED.name, sec_company.name),
    ticker = COALESCE(EXCLUDED.ticker, sec_company.ticker),
    exchange = COALESCE(EXCLUDED.exchange, sec_company.exchange),
    updated_on = NOW()
RETURNING sec_company_id AS "secCompanyId";

-- name: enrich_sec_company!
UPDATE sec_company SET
    sic = COALESCE(:sic, sic),
    sic_description = COALESCE(:sic_description, sic_description),
    state_of_incorp = COALESCE(:state_of_incorp, state_of_incorp),
    fiscal_year_end = COALESCE(:fiscal_year_end, fiscal_year_end),
    street = COALESCE(:street, street),
    city = COALESCE(:city, city),
    state_or_country = COALESCE(:state_or_country, state_or_country),
    zip_code = COALESCE(:zip_code, zip_code),
    phone = COALESCE(:phone, phone),
    website = COALESCE(:website, website),
    enriched_at = NOW(),
    updated_on = NOW()
WHERE cik = :cik;

-- name: get_sec_companies_not_enriched
SELECT sec_company_id AS "secCompanyId", cik, name, ticker, exchange
FROM sec_company
WHERE enriched_at IS NULL
ORDER BY sec_company_id
LIMIT :limit;

-- name: count_sec_companies$
SELECT COUNT(*) FROM sec_company;

-- name: count_sec_companies_not_enriched$
SELECT COUNT(*) FROM sec_company WHERE enriched_at IS NULL;

-- name: upsert_sec_company_from_issuer^
INSERT INTO sec_company (cik, name, street, city, state_or_country, zip_code, phone)
VALUES (:cik, :name, :street, :city, :state_or_country, :zip_code, :phone)
ON CONFLICT (cik) DO UPDATE SET
    name = COALESCE(EXCLUDED.name, sec_company.name),
    street = COALESCE(EXCLUDED.street, sec_company.street),
    city = COALESCE(EXCLUDED.city, sec_company.city),
    state_or_country = COALESCE(EXCLUDED.state_or_country, sec_company.state_or_country),
    zip_code = COALESCE(EXCLUDED.zip_code, sec_company.zip_code),
    phone = COALESCE(EXCLUDED.phone, sec_company.phone),
    updated_on = NOW()
RETURNING sec_company_id AS "secCompanyId";
