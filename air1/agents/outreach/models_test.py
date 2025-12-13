"""Unit tests for outreach message generation models."""

import pytest
from pydantic import ValidationError

from air1.agents.outreach.models import (
    MessageType,
    VoiceProfile,
    OutreachRules,
    MessageRequest,
    GeneratedMessage,
)


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_types(self):
        """Test all message types exist."""
        assert MessageType.CONNECTION_REQUEST.value == "connection_request"
        assert MessageType.LINKEDIN_DM.value == "linkedin_dm"
        assert MessageType.INMAIL.value == "inmail"
        assert MessageType.FOLLOW_UP.value == "follow_up"
        assert MessageType.EMAIL.value == "email"


class TestVoiceProfile:
    """Tests for VoiceProfile model."""

    def test_default_profile(self):
        """Test creating profile with defaults."""
        profile = VoiceProfile()
        assert profile.writing_samples == []
        assert profile.tone == "professional"
        assert profile.formality_level == 5
        assert profile.uses_emojis is False

    def test_full_profile(self):
        """Test creating profile with all fields."""
        profile = VoiceProfile(
            writing_samples=["Hey! Loved your post about AI.", "Quick question for you..."],
            tone="casual",
            formality_level=3,
            greeting_style="Hey",
            sign_off_style="Cheers",
            common_phrases=["love to chat", "quick question"],
            uses_emojis=True,
            uses_humor=True,
            sentence_length="short",
        )
        assert len(profile.writing_samples) == 2
        assert profile.tone == "casual"
        assert profile.formality_level == 3
        assert profile.uses_emojis is True

    def test_formality_bounds(self):
        """Test formality level must be 1-10."""
        with pytest.raises(ValidationError):
            VoiceProfile(formality_level=0)
        
        with pytest.raises(ValidationError):
            VoiceProfile(formality_level=11)

    def test_valid_formality_bounds(self):
        """Test valid formality at boundaries."""
        p1 = VoiceProfile(formality_level=1)
        p10 = VoiceProfile(formality_level=10)
        assert p1.formality_level == 1
        assert p10.formality_level == 10


class TestOutreachRules:
    """Tests for OutreachRules model."""

    def test_default_rules(self):
        """Test creating rules with defaults."""
        rules = OutreachRules()
        assert rules.dos == []
        assert rules.donts == []
        assert rules.banned_phrases == []
        assert rules.max_length is None

    def test_full_rules(self):
        """Test creating rules with all fields."""
        rules = OutreachRules(
            dos=["Mention their recent post", "Keep it under 3 sentences"],
            donts=["Don't be salesy", "Don't use corporate jargon"],
            always_mention=["our AI platform"],
            never_mention=["competitors", "pricing"],
            banned_phrases=["circle back", "synergy", "leverage"],
            required_cta="Ask for a quick chat",
            max_length=300,
        )
        assert len(rules.dos) == 2
        assert len(rules.donts) == 2
        assert "synergy" in rules.banned_phrases
        assert rules.max_length == 300


class TestMessageRequest:
    """Tests for MessageRequest model."""

    def test_minimal_request(self):
        """Test creating request with only required field."""
        request = MessageRequest(prospect_name="John Doe")
        assert request.prospect_name == "John Doe"
        assert request.message_type == MessageType.LINKEDIN_DM
        assert request.sequence_step == 1

    def test_full_request(self):
        """Test creating request with all fields."""
        request = MessageRequest(
            message_type=MessageType.CONNECTION_REQUEST,
            prospect_name="Jane Smith",
            prospect_title="VP of Sales",
            prospect_company="Acme Inc",
            prospect_summary="Jane is a sales leader with 10 years experience.",
            company_summary="Acme is a B2B SaaS company.",
            pain_points=["Scaling sales team", "Lead qualification"],
            talking_points=["Recent funding round", "Hiring spree"],
            relevancy="Strong fit for our sales automation tool.",
            outreach_trigger="Liked your post about AI in sales",
            product_description="AI-powered sales automation",
            value_proposition="10x your outbound efficiency",
            sequence_step=1,
            previous_messages=[],
        )
        assert request.message_type == MessageType.CONNECTION_REQUEST
        assert request.prospect_title == "VP of Sales"
        assert len(request.pain_points) == 2

    def test_follow_up_request(self):
        """Test creating follow-up request."""
        request = MessageRequest(
            prospect_name="John Doe",
            message_type=MessageType.FOLLOW_UP,
            sequence_step=2,
            previous_messages=["Hey John, saw your post about AI..."],
        )
        assert request.sequence_step == 2
        assert len(request.previous_messages) == 1


class TestGeneratedMessage:
    """Tests for GeneratedMessage model."""

    def test_minimal_message(self):
        """Test creating message with required fields."""
        message = GeneratedMessage(
            message="Hey John! Loved your post about AI.",
            message_type=MessageType.LINKEDIN_DM,
            character_count=35,
        )
        assert message.message.startswith("Hey")
        assert message.character_count == 35
        assert message.confidence_score == 0

    def test_full_message(self):
        """Test creating message with all fields."""
        message = GeneratedMessage(
            message="Hey John! Loved your post about AI in sales.",
            message_type=MessageType.EMAIL,
            character_count=45,
            personalization_elements=["recent post", "AI interest"],
            subject_line="Quick thought on your AI post",
            confidence_score=85,
            reasoning="Strong personalization based on recent activity",
            alternative_openers=[
                "Saw your post about AI...",
                "Your take on AI in sales resonated...",
            ],
        )
        assert message.subject_line is not None
        assert message.confidence_score == 85
        assert len(message.alternative_openers) == 2

    def test_confidence_bounds(self):
        """Test confidence score must be 0-100."""
        with pytest.raises(ValidationError):
            GeneratedMessage(
                message="Test",
                message_type=MessageType.LINKEDIN_DM,
                character_count=4,
                confidence_score=-1,
            )
        
        with pytest.raises(ValidationError):
            GeneratedMessage(
                message="Test",
                message_type=MessageType.LINKEDIN_DM,
                character_count=4,
                confidence_score=101,
            )

    def test_connection_request_no_subject(self):
        """Test connection request doesn't need subject line."""
        message = GeneratedMessage(
            message="Hey! Would love to connect.",
            message_type=MessageType.CONNECTION_REQUEST,
            character_count=28,
        )
        assert message.subject_line is None
