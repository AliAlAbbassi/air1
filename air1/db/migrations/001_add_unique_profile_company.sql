-- Migration: Add unique constraint for profile-company relationship
-- Date: 2025-11-28
-- Description: Prevents duplicate entries for the same profile-company combination
--              while allowing profiles to be associated with multiple companies

ALTER TABLE linkedin_company_members 
ADD CONSTRAINT unique_profile_company UNIQUE (linkedin_profile_id, username);
