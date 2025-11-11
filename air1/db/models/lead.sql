-- drop table lead;

create table lead
(
    lead_id      bigint generated always as identity primary key,
    first_name   varchar(255)            null,
    full_name    varchar(255)            null,
    email        varchar(255)            not null,
    phone_number varchar(255)            null,
    created_on   timestamp default now() not null,
    updated_on   timestamp default now() not null
);

create or replace function update_updated_on_column()
    returns trigger as
$$
begin
    new.updated_on = now();
    return new;
end;
$$ language plpgsql;

create trigger update_lead_updated_on
    before update
    on lead
    for each row
execute function update_updated_on_column();