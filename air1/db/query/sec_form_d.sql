-- name: upsert_sec_form_d^
INSERT INTO sec_form_d (
    sec_filing_id, issuer_name, issuer_street, issuer_city,
    issuer_state, issuer_zip, issuer_phone, entity_type,
    industry_group_type, revenue_range, federal_exemptions,
    total_offering_amount, total_amount_sold, total_remaining,
    date_of_first_sale
)
VALUES (
    :sec_filing_id, :issuer_name, :issuer_street, :issuer_city,
    :issuer_state, :issuer_zip, :issuer_phone, :entity_type,
    :industry_group_type, :revenue_range, :federal_exemptions,
    CAST(:total_offering_amount AS DECIMAL(20,2)), CAST(:total_amount_sold AS DECIMAL(20,2)), CAST(:total_remaining AS DECIMAL(20,2)),
    CAST(:date_of_first_sale AS DATE)
)
ON CONFLICT (sec_filing_id) DO UPDATE SET
    issuer_name = COALESCE(EXCLUDED.issuer_name, sec_form_d.issuer_name),
    total_offering_amount = COALESCE(EXCLUDED.total_offering_amount, sec_form_d.total_offering_amount),
    total_amount_sold = COALESCE(EXCLUDED.total_amount_sold, sec_form_d.total_amount_sold),
    updated_on = NOW()
RETURNING sec_form_d_id AS "secFormDId";

-- name: get_recent_form_d_with_officers
SELECT sfd.sec_form_d_id AS "secFormDId",
       sfd.issuer_name AS "issuerName",
       sfd.total_offering_amount AS "totalOfferingAmount",
       sfd.industry_group_type AS "industryGroupType",
       sfd.revenue_range AS "revenueRange",
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
