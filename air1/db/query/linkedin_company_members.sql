insert into linkedin_company_members (linkedin_profile_id, company_url, company_name)
values ($1, $2, $3)
on conflict (linkedin_profile_id, company_url) do update set
    company_name = coalesce(linkedin_company_members.company_name, excluded.company_name);