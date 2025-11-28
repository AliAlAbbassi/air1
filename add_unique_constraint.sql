-- Add unique constraint for linkedin_company_members
-- This allows a profile to work at multiple companies (different username values)
-- but prevents duplicate entries for the same profile-company combination
ALTER TABLE linkedin_company_members 
ADD CONSTRAINT unique_profile_company UNIQUE (linkedin_profile_id, username);
