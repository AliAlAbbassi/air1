"""Online tests for outreach message generation agents.

These tests call the actual LLM and are skipped by default.
Run with: uv run pytest air1/agents/outreach/agents_online_test.py --online -v -s
"""

import pytest
from loguru import logger

from air1.agents.outreach.models import (
    VoiceProfile,
    OutreachRules,
    MessageRequest,
    MessageType,
)
from air1.agents.outreach.crew import OutreachMessageCrew


# Sample data for testing
SAMPLE_VOICE_PROFILE = VoiceProfile(
    writing_samples=[
        "Hey! Saw your post about scaling sales teams - really resonated with me. We're tackling similar challenges at our company. Would love to swap notes if you're open to it.",
        "Quick question for you - noticed you're hiring SDRs. We built something that might help with onboarding. Mind if I share a quick overview?",
        "Love what you're building at Acme! The product-led approach is smart. Happy to chat if you ever want to brainstorm growth strategies.",
    ],
    tone="casual",
    formality_level=3,
    greeting_style="Hey",
    sign_off_style="",
    common_phrases=["love to chat", "quick question", "swap notes"],
    uses_emojis=False,
    uses_humor=False,
    sentence_length="medium",
)

SAMPLE_RULES = OutreachRules(
    dos=[
        "Reference something specific about them",
        "Keep it conversational",
        "End with a soft CTA",
    ],
    donts=[
        "Don't be salesy or pushy",
        "Don't use corporate jargon",
        "Don't make it about you",
    ],
    banned_phrases=["circle back", "synergy", "leverage", "touch base"],
    required_cta="Ask for a quick chat or their thoughts",
    max_length=500,
)

SAMPLE_REQUEST = MessageRequest(
    message_type=MessageType.LINKEDIN_DM,
    prospect_name="Sarah Chen",
    prospect_title="VP of Sales",
    prospect_company="TechCorp",
    prospect_summary="Sarah is a sales leader with 12 years experience. Previously at Salesforce and HubSpot. Known for building high-performing SDR teams.",
    company_summary="TechCorp is a Series B SaaS company ($25M raised) focused on sales enablement. Growing fast, recently expanded to 150 employees.",
    pain_points=[
        "Scaling SDR team from 5 to 20",
        "Maintaining quality while growing fast",
        "SDR onboarding taking too long",
    ],
    talking_points=[
        "Recent Series B funding",
        "Aggressive hiring plans",
        "Her LinkedIn post about SDR training",
    ],
    relevancy="Strong fit - she's scaling sales and we help with SDR productivity",
    outreach_trigger="Liked her post about SDR training challenges",
    product_description="AI-powered sales automation platform",
    value_proposition="Help SDR teams book 3x more meetings",
)


@pytest.mark.online
class TestVoiceAnalyzerOnline:
    """Online tests for voice analyzer agent."""

    def test_voice_analysis(self):
        """Test voice analysis from writing samples."""
        crew = OutreachMessageCrew()
        
        writing_samples = [
            "Hey! Quick question - saw you're scaling your sales team. We help companies like yours book more meetings. Mind if I share how?",
            "Love what you're building! The approach to outbound is refreshing. Would be great to swap notes sometime.",
            "Noticed your post about AI in sales - totally agree. We're seeing similar trends. Happy to chat if you want to compare notes.",
        ]
        
        logger.info("Testing voice analysis...")
        profile = crew.analyze_voice(writing_samples)
        
        logger.info(f"Extracted tone: {profile.tone}")
        logger.info(f"Formality level: {profile.formality_level}")
        logger.info(f"Greeting style: {profile.greeting_style}")
        logger.info(f"Uses emojis: {profile.uses_emojis}")
        logger.info(f"Sentence length: {profile.sentence_length}")
        
        assert profile is not None
        assert profile.writing_samples == writing_samples


@pytest.mark.online
class TestMessageGeneratorOnline:
    """Online tests for message generator agent."""

    def test_linkedin_dm_generation(self):
        """Test generating a LinkedIn DM."""
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        logger.info("Testing LinkedIn DM generation...")
        message = crew.generate_message(SAMPLE_REQUEST)
        
        logger.info(f"Generated message ({message.character_count} chars):")
        logger.info(f"---\n{message.message}\n---")
        logger.info(f"Confidence: {message.confidence_score}")
        logger.info(f"Personalization: {message.personalization_elements}")
        
        assert message.message is not None
        assert len(message.message) > 0
        assert message.message_type == MessageType.LINKEDIN_DM

    def test_connection_request_generation(self):
        """Test generating a connection request (300 char limit)."""
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        request = SAMPLE_REQUEST.model_copy()
        request.message_type = MessageType.CONNECTION_REQUEST
        
        logger.info("Testing connection request generation...")
        message = crew.generate_message(request)
        
        logger.info(f"Generated connection request ({message.character_count} chars):")
        logger.info(f"---\n{message.message}\n---")
        
        assert message.message is not None
        assert message.message_type == MessageType.CONNECTION_REQUEST
        # Connection requests should be concise
        logger.info(f"Character count: {message.character_count} (limit: 300)")

    def test_email_generation(self):
        """Test generating an email with subject line."""
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        request = SAMPLE_REQUEST.model_copy()
        request.message_type = MessageType.EMAIL
        
        logger.info("Testing email generation...")
        message = crew.generate_message(request)
        
        logger.info(f"Subject: {message.subject_line}")
        logger.info(f"Generated email ({message.character_count} chars):")
        logger.info(f"---\n{message.message}\n---")
        
        assert message.message is not None
        assert message.message_type == MessageType.EMAIL


@pytest.mark.online
class TestOutreachCrewOnline:
    """Online tests for full outreach crew."""

    def test_generate_message_without_voice_profile(self):
        """Test generating message without pre-defined voice profile."""
        crew = OutreachMessageCrew(outreach_rules=SAMPLE_RULES)
        
        logger.info("Testing message generation without voice profile...")
        message = crew.generate_message(SAMPLE_REQUEST)
        
        logger.info(f"Generated message ({message.character_count} chars):")
        logger.info(f"---\n{message.message}\n---")
        
        assert message.message is not None

    def test_generate_sequence(self):
        """Test generating a message sequence."""
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        logger.info("Testing sequence generation (3 messages)...")
        messages = crew.generate_sequence(SAMPLE_REQUEST, num_messages=2)
        
        for i, msg in enumerate(messages, 1):
            logger.info(f"\n--- Message {i} ({msg.message_type.value}) ---")
            logger.info(f"{msg.message}")
        
        assert len(messages) == 2
        assert messages[0].message_type == MessageType.LINKEDIN_DM
        assert messages[1].message_type == MessageType.FOLLOW_UP
