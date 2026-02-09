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
    sic = :sic,
    sic_description = :sic_description,
    state_of_incorp = :state_of_incorp,
    fiscal_year_end = :fiscal_year_end,
    street = :street,
    city = :city,
    state_or_country = :state_or_country,
    zip_code = :zip_code,
    phone = :phone,
    website = :website,
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
