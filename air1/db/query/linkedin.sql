-- name: insert_linkedin_profile^
insert into linkedin_profile (lead_id, username, location, headline, about)
values (:lead_id, :username, :location, :headline, :about)
on conflict (username) do update set
    location = coalesce(linkedin_profile.location, excluded.location),
    headline = coalesce(linkedin_profile.headline, excluded.headline),
    about = coalesce(linkedin_profile.about, excluded.about)
returning linkedin_profile_id;

-- name: get_linkedin_profile_by_username^
select linkedin_profile_id, lead_id, username, location, headline, about, created_on, updated_on
from linkedin_profile
where username = :username;

-- name: get_company_leads_by_headline
select lp.lead_id, cm.username as company_name, lp.username, lp.headline, l.first_name, l.full_name, l.email
from linkedin_profile lp
         inner join lead l on l.lead_id = lp.lead_id
         join linkedin_company_members cm on cm.linkedin_profile_id = lp.linkedin_profile_id
where cm.username = :company_username
  and lp.headline ilike '%' || :search_term || '%';

-- name: get_company_leads
select lp.lead_id, cm.username as company_name, lp.username, lp.headline, l.first_name, l.full_name, l.email
from linkedin_profile lp
         inner join lead l on l.lead_id = lp.lead_id
         join linkedin_company_members cm on cm.linkedin_profile_id = lp.linkedin_profile_id
where cm.username = :company_username;