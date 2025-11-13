-- name: insert_lead^
insert into lead (first_name, full_name, email, phone_number)
values (:first_name, :full_name, :email, :phone_number)
on conflict (email) do update set first_name   = coalesce(lead.first_name, excluded.first_name),
                                  full_name    = coalesce(lead.full_name, excluded.full_name),
                                  phone_number = coalesce(lead.phone_number, excluded.phone_number)
returning lead_id;

-- name: select_all_leads
select *
from lead;