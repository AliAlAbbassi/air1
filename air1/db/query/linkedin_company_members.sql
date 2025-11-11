-- name: insert_linkedin_company_member!
insert into linkedin_company_members (linkedin_profile_id, company_url, company_name)
values (:linkedin_profile_id, :company_url, :company_name)
on conflict (linkedin_profile_id, company_url) do update set
    company_name = coalesce(linkedin_company_members.company_name, excluded.company_name);