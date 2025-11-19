-- name: insert_lead^
insert into lead (first_name, full_name, email, phone_number)
values (:first_name, :full_name, nullif(:email, ''), :phone_number)
on conflict (email) do update set
    first_name = CASE
        WHEN lead.first_name IS NULL OR lead.first_name = '' THEN excluded.first_name
        ELSE lead.first_name
    END,
    full_name = CASE
        WHEN lead.full_name IS NULL OR lead.full_name = '' THEN excluded.full_name
        ELSE lead.full_name
    END,
    phone_number = coalesce(lead.phone_number, excluded.phone_number)
returning lead_id;

-- name: select_all_leads
select *
from lead;