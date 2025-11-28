-- name: insert_linkedin_company_member!
insert into linkedin_company_members (linkedin_profile_id, username, title)
values (:linkedin_profile_id, :username, :title)
on conflict (linkedin_profile_id, username) do update set
    title = coalesce(excluded.title, linkedin_company_members.title),
    updated_on = now();

-- name: get_company_members_by_username
select company_member_id as "companyMemberId", linkedin_profile_id as "linkedinProfileId", username, title, created_on as "createdOn", updated_on as "updatedOn"
from linkedin_company_members
where username = :username;

-- name: get_company_member_by_profile_and_username^
select company_member_id as "companyMemberId", linkedin_profile_id as "linkedinProfileId", username, title, created_on as "createdOn", updated_on as "updatedOn"
from linkedin_company_members
where linkedin_profile_id = :linkedin_profile_id and username = :username;