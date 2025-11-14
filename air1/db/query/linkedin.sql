-- name: insert_linkedin_profile^
insert into linkedin_profile (lead_id, username, location, headline, about)
values (:lead_id, :username, :location, :headline, :about)
on conflict (username) do update set
    location = coalesce(linkedin_profile.location, excluded.location),
    headline = coalesce(linkedin_profile.headline, excluded.headline),
    about = coalesce(linkedin_profile.about, excluded.about)
returning linkedin_profile_id;

-- name: get_linkedin_profile_by_username
select linkedin_profile_id, lead_id, username, location, headline, about, created_on, updated_on
from linkedin_profile
where username = :username;