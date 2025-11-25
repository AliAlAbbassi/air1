-- name: insert_linkedin_profile^
insert into linkedin_profile (lead_id, username, location, headline, about)
values (:lead_id, :username, :location, :headline, :about)
on conflict (username) do update set
    location = coalesce(excluded.location, linkedin_profile.location),
    headline = coalesce(excluded.headline, linkedin_profile.headline),
    about = coalesce(excluded.about, linkedin_profile.about)
returning linkedin_profile_id as "linkedinProfileId";

-- name: get_linkedin_profile_by_username^
select linkedin_profile_id as "linkedinProfileId", lead_id as "leadId", username, location, headline, about, created_on as "createdOn", updated_on as "updatedOn"
from linkedin_profile
where username = :username;

-- name: get_company_leads_by_headline
select lp.lead_id, cm.username as company_name, lp.username, lp.headline, l.first_name, l.full_name, l.email
from linkedin_profile lp
         inner join lead l on l.lead_id = lp.lead_id
         join linkedin_company_members cm on cm.linkedin_profile_id = lp.linkedin_profile_id
where cm.username = :company_username
  and lp.headline ilike '%' || :search_term || '%'
limit :limit;

-- name: get_company_leads
select lp.lead_id, cm.username as company_name, lp.username, lp.headline, l.first_name, l.full_name, l.email
from linkedin_profile lp
         inner join lead l on l.lead_id = lp.lead_id
         join linkedin_company_members cm on cm.linkedin_profile_id = lp.linkedin_profile_id
where cm.username = :company_username;