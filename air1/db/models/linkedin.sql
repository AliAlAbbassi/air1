create table linkedin_profile
(
    linkedin_profile_id bigint generated always as identity primary key,
    lead_id             bigint references lead (lead_id),
    username            varchar(255)            not null unique,
    location            text                    null,
    headline            text                    null,
    about               text                    null,
    created_on          timestamp default now() not null,
    updated_on          timestamp default now() not null
);

create trigger update_linkedin_profile_updated_on
    before update
    on linkedin_profile
    for each row
execute function update_updated_on_column();


create table linkedin_company_members
(
    company_member_id   bigint generated always as identity primary key,
    linkedin_profile_id bigint references linkedin_profile(linkedin_profile_id),
    username            varchar(255)            not null,
    title               varchar(255)            null,
    created_on          timestamp default now() not null,
    updated_on          timestamp default now() not null,
    unique(linkedin_profile_id, username)
);

create trigger update_linkedin_company_members_updated_on
    before update
    on linkedin_company_members
    for each row
execute function update_updated_on_column();