-- name: get_writing_style_by_id^
-- Get a writing style by ID
SELECT 
    writing_style_id AS "writingStyleId",
    user_id AS "userId",
    name,
    tone,
    example_messages AS "exampleMessages",
    instructions,
    dos,
    donts,
    selected_template AS "selectedTemplate",
    advanced_questions AS "advancedQuestions",
    formality_level AS "formalityLevel",
    common_phrases AS "commonPhrases",
    greeting_style AS "greetingStyle",
    sign_off_style AS "signOffStyle",
    uses_emojis AS "usesEmojis",
    uses_humor AS "usesHumor",
    sentence_length AS "sentenceLength",
    personal_anecdotes AS "personalAnecdotes",
    signature_opener AS "signatureOpener",
    created_on AS "createdOn",
    updated_on AS "updatedOn"
FROM writing_style
WHERE writing_style_id = :writing_style_id;

-- name: get_writing_styles_by_user^
-- Get all writing styles for a user
SELECT 
    writing_style_id AS "writingStyleId",
    user_id AS "userId",
    name,
    tone,
    example_messages AS "exampleMessages",
    instructions,
    dos,
    donts,
    selected_template AS "selectedTemplate",
    advanced_questions AS "advancedQuestions",
    formality_level AS "formalityLevel",
    common_phrases AS "commonPhrases",
    greeting_style AS "greetingStyle",
    sign_off_style AS "signOffStyle",
    uses_emojis AS "usesEmojis",
    uses_humor AS "usesHumor",
    sentence_length AS "sentenceLength",
    personal_anecdotes AS "personalAnecdotes",
    signature_opener AS "signatureOpener",
    created_on AS "createdOn",
    updated_on AS "updatedOn"
FROM writing_style
WHERE user_id = :user_id
ORDER BY created_on DESC;

-- name: update_writing_style_voice_profile!
-- Update voice profile fields for a writing style
UPDATE writing_style
SET 
    tone = COALESCE(:tone, tone),
    formality_level = COALESCE(:formality_level, formality_level),
    example_messages = COALESCE(:example_messages, example_messages),
    common_phrases = COALESCE(:common_phrases, common_phrases),
    greeting_style = COALESCE(:greeting_style, greeting_style),
    sign_off_style = COALESCE(:sign_off_style, sign_off_style),
    uses_emojis = COALESCE(:uses_emojis, uses_emojis),
    uses_humor = COALESCE(:uses_humor, uses_humor),
    sentence_length = COALESCE(:sentence_length, sentence_length),
    updated_on = NOW()
WHERE writing_style_id = :writing_style_id;

-- name: update_writing_style_rules!
-- Update dos/donts rules for a writing style
UPDATE writing_style
SET 
    dos = COALESCE(:dos, dos),
    donts = COALESCE(:donts, donts),
    instructions = COALESCE(:instructions, instructions),
    updated_on = NOW()
WHERE writing_style_id = :writing_style_id;

-- name: update_writing_style_advanced_questions!
-- Update advanced questions for a writing style
UPDATE writing_style
SET 
    advanced_questions = :advanced_questions,
    updated_on = NOW()
WHERE writing_style_id = :writing_style_id;
