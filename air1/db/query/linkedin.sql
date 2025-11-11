insert into linkedin_profile (lead_id, linkedin_url, location, headline, about)
values ($1, $2, $3, $4, $5)
on conflict (linkedin_url) do update set
    location = coalesce(linkedin_profile.location, excluded.location),
    headline = coalesce(linkedin_profile.headline, excluded.headline),
    about = coalesce(linkedin_profile.about, excluded.about)
returning linkedin_profile_id;