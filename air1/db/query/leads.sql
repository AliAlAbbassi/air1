-- name: insert_lead^
insert into lead (first_name, full_name, email, phone_number)
values (:first_name, :full_name, nullif(:email, ''), :phone_number)
on conflict (email) do update set
    first_name = coalesce(excluded.first_name, lead.first_name),
    full_name = coalesce(excluded.full_name, lead.full_name),
    phone_number = coalesce(excluded.phone_number, lead.phone_number)
returning lead_id as "leadId";

-- name: select_all_leads
select *
from lead;