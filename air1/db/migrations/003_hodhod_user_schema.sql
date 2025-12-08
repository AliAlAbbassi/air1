-- Migration: Fix hodhod_user and update FKs to reference hodhod_user instead of user

-- ============================================================================
-- FIX HODHOD_USER TABLE
-- ============================================================================

ALTER TABLE hodhod_user DROP COLUMN IF EXISTS full_name;
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS auth_method VARCHAR(50);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS first_name VARCHAR(255);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS last_name VARCHAR(255);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS timezone VARCHAR(50);
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS meeting_link TEXT;
ALTER TABLE hodhod_user ADD COLUMN IF NOT EXISTS linkedin_connected BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_hodhod_user_email ON hodhod_user(email);

-- ============================================================================
-- UPDATE PRODUCT TABLE FK
-- ============================================================================

ALTER TABLE product DROP CONSTRAINT IF EXISTS product_user_id_fkey;
ALTER TABLE product ADD CONSTRAINT product_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES hodhod_user(user_id) ON DELETE RESTRICT;
ALTER TABLE product ADD COLUMN IF NOT EXISTS competitors TEXT;

-- ============================================================================
-- UPDATE WRITING_STYLE TABLE FK
-- ============================================================================

ALTER TABLE writing_style DROP CONSTRAINT IF EXISTS writing_style_user_id_fkey;
ALTER TABLE writing_style ADD CONSTRAINT writing_style_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES hodhod_user(user_id) ON DELETE RESTRICT;
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS dos TEXT[];
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS donts TEXT[];
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS selected_template VARCHAR(255);

-- ============================================================================
-- UPDATE COMPANY TABLE
-- ============================================================================

ALTER TABLE company ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES hodhod_user(user_id) ON DELETE SET NULL;
ALTER TABLE company ADD COLUMN IF NOT EXISTS description TEXT;
CREATE INDEX IF NOT EXISTS idx_company_user ON company(user_id);
