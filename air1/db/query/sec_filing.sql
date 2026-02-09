-- name: upsert_sec_filing^
INSERT INTO sec_filing (accession_number, cik, form_type, filing_date, company_name, sec_company_id)
VALUES (
    :accession_number, :cik, :form_type, :filing_date, :company_name,
    (SELECT sec_company_id FROM sec_company WHERE cik = :cik)
)
ON CONFLICT (accession_number) DO UPDATE SET
    form_type = EXCLUDED.form_type,
    company_name = COALESCE(EXCLUDED.company_name, sec_filing.company_name),
    updated_on = NOW()
RETURNING sec_filing_id AS "secFilingId";

-- name: get_form_d_filings_not_parsed
SELECT sf.sec_filing_id AS "secFilingId",
       sf.accession_number AS "accessionNumber",
       sf.cik,
       sf.form_type AS "formType",
       sf.filing_date AS "filingDate",
       sf.company_name AS "companyName"
FROM sec_filing sf
LEFT JOIN sec_form_d sfd ON sfd.sec_filing_id = sf.sec_filing_id
WHERE sf.form_type IN ('D', 'D/A')
  AND sfd.sec_form_d_id IS NULL
ORDER BY sf.filing_date DESC
LIMIT :limit;
