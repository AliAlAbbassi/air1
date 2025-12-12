-- Migration: Add advanced writing style columns
-- Description: Adds advanced_questions for user Q&A and ensures all columns exist

-- ============================================================================
-- UPDATE WRITING_STYLE TABLE
-- ============================================================================

-- Add advanced_questions column for optional Q&A from user
-- Format: JSONB array of {question: string, answer: string}
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS advanced_questions JSONB DEFAULT '[]'::jsonb;

-- Ensure example_messages exists (for voice cloning samples)
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS example_messages TEXT[];

-- Ensure instructions exists
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS instructions TEXT;

-- Add formality_level for more precise voice matching
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS formality_level INTEGER DEFAULT 5;

-- Add common_phrases for style patterns
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS common_phrases TEXT[];

-- Add greeting_style and sign_off_style
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS greeting_style VARCHAR(100);
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS sign_off_style VARCHAR(100);

-- Add uses_emojis and uses_humor flags
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS uses_emojis BOOLEAN DEFAULT FALSE;
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS uses_humor BOOLEAN DEFAULT FALSE;

-- Add sentence_length preference
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS sentence_length VARCHAR(20) DEFAULT 'medium';

-- Add personal_anecdotes for stories/references the user likes to use
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS personal_anecdotes TEXT[];

-- Add signature_opener for their typical opening line style
ALTER TABLE writing_style ADD COLUMN IF NOT EXISTS signature_opener TEXT;

-- Add index for user lookup
CREATE INDEX IF NOT EXISTS idx_writing_style_user_id ON writing_style(user_id);

COMMENT ON COLUMN writing_style.advanced_questions IS 'Optional Q&A from user for deeper personalization, stored as JSONB array of {question, answer}';
COMMENT ON COLUMN writing_style.formality_level IS 'Formality level 1-10 (1=very casual, 10=very formal)';
COMMENT ON COLUMN writing_style.sentence_length IS 'Preferred sentence length: short, medium, long';
