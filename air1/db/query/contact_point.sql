-- name: insert_contact_point_type^
insert into contact_point_types (contact_point_type)
values (:contact_point_type)
returning contact_point_types_id;

-- name: insert_contact_point^
insert into contact_point (lead_id, contact_point_type_id)
values (:lead_id, :contact_point_type_id)
returning contact_point_id;

-- name: has_linkedin_connection_by_username^
SELECT EXISTS (
    SELECT 1 
    FROM contact_point cp
    JOIN lead l ON l.lead_id = cp.lead_id
    JOIN linkedin_profile lp ON lp.lead_id = l.lead_id
    WHERE lp.username = :username
      AND cp.contact_point_type_id = 1  -- linkedin_connection type
) as "exists";
