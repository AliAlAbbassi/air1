-- name: get_user_by_email^
-- Get user by email (only essential columns for auth check)
SELECT user_id, email, password_hash, auth_method
FROM hodhod_user
WHERE email = :email;

-- name: insert_user<!
-- Insert a new user and return the user_id
-- On conflict (duplicate email), do nothing and return null
INSERT INTO hodhod_user (
    email, password_hash, auth_method, first_name, last_name,
    timezone, meeting_link, linkedin_connected
)
VALUES (
    :email, :password_hash, :auth_method, :first_name, :last_name,
    :timezone, :meeting_link, :linkedin_connected
)
ON CONFLICT (email) DO NOTHING
RETURNING user_id AS "userId";

-- name: insert_user_company<!
-- Insert user's company and return company_id
-- On conflict (duplicate linkedin_username), update and return existing
INSERT INTO company (
    name, linkedin_username, website, industry, size, description, user_id
)
VALUES (
    :name, :linkedin_username, :website, :industry, :size, :description, :user_id
)
ON CONFLICT (linkedin_username) WHERE linkedin_username IS NOT NULL DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website,
    industry = EXCLUDED.industry,
    size = EXCLUDED.size,
    description = EXCLUDED.description,
    user_id = EXCLUDED.user_id,
    updated_on = NOW()
RETURNING company_id AS "companyId";

-- name: insert_user_product<!
-- Insert user's product and return product_id
INSERT INTO product (
    user_id, name, website_url, description, target_icp, competitors
)
VALUES (
    :user_id, :name, :website_url, :description, :target_icp, :competitors
)
RETURNING product_id AS "productId";

-- name: insert_user_writing_style<!
-- Insert user's writing style and return writing_style_id
INSERT INTO writing_style (
    user_id, name, tone, dos, donts, selected_template
)
VALUES (
    :user_id, :name, :tone, :dos, :donts, :selected_template
)
RETURNING writing_style_id AS "writingStyleId";
