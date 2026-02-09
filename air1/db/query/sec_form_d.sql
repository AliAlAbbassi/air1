-- name: upsert_sec_form_d^
INSERT INTO sec_form_d (
    sec_filing_id, issuer_name, issuer_street, issuer_city,
    issuer_state, issuer_zip, issuer_phone, entity_type,
    industry_group_type, revenue_range, federal_exemptions,
    total_offering_amount, total_amount_sold, total_remaining,
    date_of_first_sale, minimum_investment, total_investors,
    has_non_accredited_investors, is_equity, is_pooled_investment,
    is_new_offering, more_than_one_year, is_business_combination,
    sales_commission, finders_fees, gross_proceeds_used
)
VALUES (
    :sec_filing_id, :issuer_name, :issuer_street, :issuer_city,
    :issuer_state, :issuer_zip, :issuer_phone, :entity_type,
    :industry_group_type, :revenue_range, :federal_exemptions,
    CAST(:total_offering_amount AS DECIMAL(20,2)), CAST(:total_amount_sold AS DECIMAL(20,2)), CAST(:total_remaining AS DECIMAL(20,2)),
    CAST(:date_of_first_sale AS DATE), CAST(:minimum_investment AS DECIMAL(20,2)), CAST(:total_investors AS INTEGER),
    CAST(:has_non_accredited_investors AS BOOLEAN), CAST(:is_equity AS BOOLEAN), CAST(:is_pooled_investment AS BOOLEAN),
    CAST(:is_new_offering AS BOOLEAN), CAST(:more_than_one_year AS BOOLEAN), CAST(:is_business_combination AS BOOLEAN),
    CAST(:sales_commission AS DECIMAL(20,2)), CAST(:finders_fees AS DECIMAL(20,2)), CAST(:gross_proceeds_used AS DECIMAL(20,2))
)
ON CONFLICT (sec_filing_id) DO UPDATE SET
    issuer_name = COALESCE(EXCLUDED.issuer_name, sec_form_d.issuer_name),
    total_offering_amount = COALESCE(EXCLUDED.total_offering_amount, sec_form_d.total_offering_amount),
    total_amount_sold = COALESCE(EXCLUDED.total_amount_sold, sec_form_d.total_amount_sold),
    minimum_investment = COALESCE(EXCLUDED.minimum_investment, sec_form_d.minimum_investment),
    total_investors = COALESCE(EXCLUDED.total_investors, sec_form_d.total_investors),
    has_non_accredited_investors = COALESCE(EXCLUDED.has_non_accredited_investors, sec_form_d.has_non_accredited_investors),
    is_equity = COALESCE(EXCLUDED.is_equity, sec_form_d.is_equity),
    is_pooled_investment = COALESCE(EXCLUDED.is_pooled_investment, sec_form_d.is_pooled_investment),
    is_new_offering = COALESCE(EXCLUDED.is_new_offering, sec_form_d.is_new_offering),
    more_than_one_year = COALESCE(EXCLUDED.more_than_one_year, sec_form_d.more_than_one_year),
    is_business_combination = COALESCE(EXCLUDED.is_business_combination, sec_form_d.is_business_combination),
    sales_commission = COALESCE(EXCLUDED.sales_commission, sec_form_d.sales_commission),
    finders_fees = COALESCE(EXCLUDED.finders_fees, sec_form_d.finders_fees),
    gross_proceeds_used = COALESCE(EXCLUDED.gross_proceeds_used, sec_form_d.gross_proceeds_used),
    updated_on = NOW()
RETURNING sec_form_d_id AS "secFormDId";

-- name: get_recent_form_d_with_officers
SELECT sfd.sec_form_d_id AS "secFormDId",
       sfd.issuer_name AS "issuerName",
       sfd.total_offering_amount AS "totalOfferingAmount",
       sfd.industry_group_type AS "industryGroupType",
       sfd.revenue_range AS "revenueRange",
       sfd.minimum_investment AS "minimumInvestment",
       sfd.total_investors AS "totalInvestors",
       sfd.is_equity AS "isEquity",
       sfd.is_new_offering AS "isNewOffering",
       sf.filing_date AS "filingDate",
       sf.cik,
       so.first_name AS "officerFirstName",
       so.last_name AS "officerLastName",
       so.title AS "officerTitle"
FROM sec_form_d sfd
JOIN sec_filing sf ON sf.sec_filing_id = sfd.sec_filing_id
LEFT JOIN sec_officer so ON so.sec_form_d_id = sfd.sec_form_d_id
WHERE sf.filing_date >= :since_date
ORDER BY sf.filing_date DESC
LIMIT :limit;
