-- name: insert_company^
INSERT INTO company (name, linkedin_username, source, job_geo_id)
VALUES (:name, :linkedin_username, :source, :job_geo_id)
ON CONFLICT (linkedin_username) DO UPDATE SET
    name = COALESCE(EXCLUDED.name, company.name),
    source = COALESCE(EXCLUDED.source, company.source),
    job_geo_id = COALESCE(EXCLUDED.job_geo_id, company.job_geo_id),
    updated_on = NOW()
RETURNING company_id as "companyId";

-- name: insert_company_by_name^
INSERT INTO company (name, source, job_geo_id)
VALUES (:name, :source, :job_geo_id)
ON CONFLICT DO NOTHING
RETURNING company_id as "companyId";

-- name: get_company_by_name^
SELECT company_id as "companyId", name, linkedin_username as "linkedinUsername", 
       website, industry, size, source, job_geo_id as "jobGeoId",
       created_on as "createdOn", updated_on as "updatedOn"
FROM company
WHERE name = :name;

-- name: get_company_by_linkedin_username^
SELECT company_id as "companyId", name, linkedin_username as "linkedinUsername",
       website, industry, size, source, job_geo_id as "jobGeoId",
       created_on as "createdOn", updated_on as "updatedOn"
FROM company
WHERE linkedin_username = :linkedin_username;

-- name: get_companies_by_source
SELECT company_id as "companyId", name, linkedin_username as "linkedinUsername",
       website, industry, size, source, job_geo_id as "jobGeoId",
       created_on as "createdOn", updated_on as "updatedOn"
FROM company
WHERE source = :source
ORDER BY created_on DESC;

-- name: upsert_company_outreach^
INSERT INTO company_outreach (company_id, status, employees_contacted, notes)
VALUES (:company_id, :status, :employees_contacted, :notes)
ON CONFLICT (company_id) DO UPDATE SET
    status = COALESCE(EXCLUDED.status, company_outreach.status),
    employees_contacted = COALESCE(EXCLUDED.employees_contacted, company_outreach.employees_contacted),
    notes = COALESCE(EXCLUDED.notes, company_outreach.notes),
    updated_on = NOW()
RETURNING company_outreach_id as "companyOutreachId";

-- name: get_company_outreach_status^
SELECT co.company_outreach_id as "companyOutreachId", co.company_id as "companyId",
       co.status, co.employees_contacted as "employeesContacted", co.notes,
       c.name as "companyName", c.linkedin_username as "linkedinUsername"
FROM company_outreach co
JOIN company c ON c.company_id = co.company_id
WHERE co.company_id = :company_id;

-- name: get_companies_with_outreach_status
SELECT c.company_id as "companyId", c.name, c.linkedin_username as "linkedinUsername",
       c.source, c.job_geo_id as "jobGeoId",
       COALESCE(co.status, 'not_started') as status,
       COALESCE(co.employees_contacted, 0) as "employeesContacted"
FROM company c
LEFT JOIN company_outreach co ON co.company_id = c.company_id
WHERE (:source IS NULL OR c.source = :source)
ORDER BY c.created_on DESC;

-- name: increment_employees_contacted^
UPDATE company_outreach
SET employees_contacted = employees_contacted + 1,
    updated_on = NOW()
WHERE company_id = :company_id
RETURNING employees_contacted as "employeesContacted";

-- name: update_outreach_status^
UPDATE company_outreach
SET status = :status,
    updated_on = NOW()
WHERE company_id = :company_id
RETURNING company_outreach_id as "companyOutreachId";

