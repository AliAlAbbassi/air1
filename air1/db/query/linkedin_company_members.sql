-- name: insert_linkedin_company_member!
insert into linkedin_company_members (linkedin_profile_id, username, title)
values (:linkedin_profile_id, :username, :title)
on conflict (linkedin_profile_id, username) do update set
    title = coalesce(linkedin_company_members.title, excluded.title);