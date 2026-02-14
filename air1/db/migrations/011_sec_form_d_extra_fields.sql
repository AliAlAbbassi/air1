-- Migration: Add extra Form D fields + clean up test data

-- New offering detail columns
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS minimum_investment DECIMAL(20,2);
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS total_investors INTEGER;
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS has_non_accredited_investors BOOLEAN;
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS is_equity BOOLEAN;
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS is_pooled_investment BOOLEAN;
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS is_new_offering BOOLEAN;
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS more_than_one_year BOOLEAN;
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS is_business_combination BOOLEAN;
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS sales_commission DECIMAL(20,2);
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS finders_fees DECIMAL(20,2);
ALTER TABLE sec_form_d ADD COLUMN IF NOT EXISTS gross_proceeds_used DECIMAL(20,2);

-- Clean up test data with fake CIKs (non-numeric)
DELETE FROM sec_company WHERE cik !~ '^[0-9]+$';
