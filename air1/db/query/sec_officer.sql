-- name: delete_officers_by_form_d!
DELETE FROM sec_officer WHERE sec_form_d_id = :sec_form_d_id;

-- name: insert_sec_officer^
INSERT INTO sec_officer (sec_form_d_id, first_name, last_name, title, street, city, state, zip_code)
VALUES (:sec_form_d_id, :first_name, :last_name, :title, :street, :city, :state, :zip_code)
RETURNING sec_officer_id AS "secOfficerId";
