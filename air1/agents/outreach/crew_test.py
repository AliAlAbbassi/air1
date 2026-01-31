"""Unit tests for OutreachMessageCrew."""


from air1.agents.outreach.models import (
    VoiceProfile,
    OutreachRules,
    MessageType,
    AdvancedQuestion,
    WritingStyleRecord,
)
from air1.agents.outreach.crew import OutreachMessageCrew


class TestOutreachMessageCrew:
    """Tests for OutreachMessageCrew initialization."""

    def test_init_default(self):
        """Test crew initializes with defaults."""
        crew = OutreachMessageCrew()
        assert crew.voice_profile is not None
        assert crew.outreach_rules is not None
        assert crew.message_generator is not None

    def test_init_with_voice_profile(self):
        """Test crew initializes with custom voice profile."""
        profile = VoiceProfile(
            tone="casual",
            formality_level=3,
            uses_emojis=True,
        )
        crew = OutreachMessageCrew(voice_profile=profile)
        assert crew.voice_profile.tone == "casual"
        assert crew.voice_profile.formality_level == 3

    def test_init_with_outreach_rules(self):
        """Test crew initializes with custom rules."""
        rules = OutreachRules(
            dos=["Be friendly"],
            donts=["Be pushy"],
            banned_phrases=["synergy"],
        )
        crew = OutreachMessageCrew(outreach_rules=rules)
        assert "Be friendly" in crew.outreach_rules.dos
        assert "synergy" in crew.outreach_rules.banned_phrases


class TestParseVoiceProfile:
    """Tests for voice profile parsing."""

    def test_parse_casual_tone(self):
        """Test parsing casual tone from output."""
        crew = OutreachMessageCrew()
        samples = ["Hey! Quick question..."]
        
        raw_output = """
        Tone: casual and friendly
        Formality: 3
        Greeting style: "Hey"
        Uses emojis occasionally
        Sentence length: short
        """
        
        profile = crew._parse_voice_profile(raw_output, samples)
        assert profile.tone == "casual"
        assert profile.writing_samples == samples

    def test_parse_formal_tone(self):
        """Test parsing formal tone from output."""
        crew = OutreachMessageCrew()
        
        raw_output = """
        Tone: formal and professional
        Formality: 8
        """
        
        profile = crew._parse_voice_profile(raw_output, [])
        assert profile.tone == "formal"


class TestParseGeneratedMessage:
    """Tests for message parsing."""

    def test_parse_basic_message(self):
        """Test parsing a basic message."""
        crew = OutreachMessageCrew()
        
        raw_output = """
        Generated message:
        Hey Sarah! Loved your post about scaling SDR teams.
        
        Character count: 52
        Confidence: 85
        """
        
        message = crew._parse_generated_message(raw_output, MessageType.LINKEDIN_DM)
        assert message.message is not None
        assert message.message_type == MessageType.LINKEDIN_DM

    def test_parse_with_subject_line(self):
        """Test parsing message with subject line."""
        crew = OutreachMessageCrew()
        
        raw_output = """
        Subject: Quick thought on your SDR post
        
        Message:
        Hey Sarah! Loved your post about scaling SDR teams.
        
        Confidence: 90
        """
        
        message = crew._parse_generated_message(raw_output, MessageType.EMAIL)
        assert message.message_type == MessageType.EMAIL


class TestExtractMessageText:
    """Tests for message text extraction."""

    def test_extract_quoted_message(self):
        """Test extracting quoted message."""
        crew = OutreachMessageCrew()
        
        raw = 'message: "Hey Sarah! Great post."'
        text = crew._extract_message_text(raw)
        assert "Sarah" in text or "Hey" in text

    def test_extract_from_section(self):
        """Test extracting from message section."""
        crew = OutreachMessageCrew()
        
        raw = """
        Generated message:
        Hey Sarah! Loved your post.
        Would love to chat sometime.
        
        Character count: 50
        """
        
        text = crew._extract_message_text(raw)
        assert len(text) > 0


class TestWritingStyleRecord:
    """Tests for WritingStyleRecord conversion."""

    def test_to_voice_profile(self):
        """Test converting record to VoiceProfile."""
        record = WritingStyleRecord(
            writingStyleId=1,
            userId=1,
            name="Default",
            tone="casual",
            exampleMessages=["Hey! Quick question..."],
            formalityLevel=3,
            greetingStyle="Hey",
            usesEmojis=True,
        )
        
        profile = record.to_voice_profile()
        assert profile.tone == "casual"
        assert profile.formality_level == 3
        assert profile.greeting_style == "Hey"
        assert profile.uses_emojis is True
        assert len(profile.writing_samples) == 1

    def test_to_outreach_rules(self):
        """Test converting record to OutreachRules."""
        record = WritingStyleRecord(
            writingStyleId=1,
            userId=1,
            name="Default",
            dos=["Be friendly", "Keep it short"],
            donts=["Be pushy"],
            instructions="Focus on value",
            advancedQuestions=[
                {"question": "What's your USP?", "answer": "AI-powered automation"},
            ],
        )
        
        rules = record.to_outreach_rules()
        assert len(rules.dos) == 2
        assert len(rules.donts) == 1
        assert rules.instructions == "Focus on value"
        assert len(rules.advanced_questions) == 1
        assert rules.advanced_questions[0].question == "What's your USP?"

    def test_to_voice_profile_with_defaults(self):
        """Test converting record with missing fields uses defaults."""
        record = WritingStyleRecord(
            writingStyleId=1,
            userId=1,
            name="Default",
        )
        
        profile = record.to_voice_profile()
        assert profile.tone == "professional"
        assert profile.formality_level == 5
        assert profile.writing_samples == []

    def test_to_outreach_rules_with_defaults(self):
        """Test converting record with missing fields uses defaults."""
        record = WritingStyleRecord(
            writingStyleId=1,
            userId=1,
            name="Default",
        )
        
        rules = record.to_outreach_rules()
        assert rules.dos == []
        assert rules.donts == []
        assert rules.advanced_questions == []


class TestAdvancedQuestions:
    """Tests for advanced questions in rules."""

    def test_advanced_questions_in_rules(self):
        """Test advanced questions are included in rules."""
        rules = OutreachRules(
            dos=["Be friendly"],
            advanced_questions=[
                AdvancedQuestion(question="What problem do you solve?", answer="Lead qualification"),
                AdvancedQuestion(question="Who is your ICP?", answer="Sales leaders"),
            ],
        )
        
        assert len(rules.advanced_questions) == 2
        assert rules.advanced_questions[0].answer == "Lead qualification"
