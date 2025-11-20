-- name: insert_contact_point_type^
insert into contact_point_types (contact_point_type)
values (:contact_point_type)
returning contact_point_types_id;

-- name: insert_contact_point^
insert into contact_point (lead_id, contact_point_type_id)
values (:lead_id, :contact_point_type_id)
returning contact_point_id;
