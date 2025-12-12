"""Online tests for outreach message generation agents.

These tests call the actual LLM and are skipped by default.
Run with: uv run pytest air1/agents/outreach/agents_online_test.py --online -v -s
"""

import pytest

from air1.agents.outreach.models import (
    VoiceProfile,
    OutreachRules,
    MessageRequest,
    MessageType,
    AdvancedQuestion,
)
from air1.agents.outreach.crew import OutreachMessageCrew


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_message(message, label: str = "Generated Message"):
    """Print a formatted message output."""
    print(f"\n{'-'*50}")
    print(f"  {label}")
    print(f"{'-'*50}")
    print(f"\n{message.message}\n")
    print(f"{'-'*50}")
    print(f"  Type: {message.message_type.value}")
    print(f"  Characters: {message.character_count}")
    if message.subject_line:
        print(f"  Subject: {message.subject_line}")
    print(f"  Confidence: {message.confidence_score}/100")
    if message.personalization_elements:
        print(f"  Personalization: {', '.join(message.personalization_elements)}")
    if message.reasoning:
        print(f"  Reasoning: {message.reasoning}")
    if message.alternative_openers:
        print(f"  Alternative openers:")
        for alt in message.alternative_openers:
            print(f"    - {alt}")
    print(f"{'-'*50}\n")


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
        print_header("VOICE ANALYSIS TEST")
        
        crew = OutreachMessageCrew()
        
        writing_samples = [
            "Hey! Quick question - saw you're scaling your sales team. We help companies like yours book more meetings. Mind if I share how?",
            "Love what you're building! The approach to outbound is refreshing. Would be great to swap notes sometime.",
            "Noticed your post about AI in sales - totally agree. We're seeing similar trends. Happy to chat if you want to compare notes.",
        ]
        
        print("Input writing samples:")
        for i, sample in enumerate(writing_samples, 1):
            print(f"  {i}. \"{sample}\"")
        
        profile = crew.analyze_voice(writing_samples)
        
        print("\n" + "="*50)
        print("  EXTRACTED VOICE PROFILE")
        print("="*50)
        print(f"  Tone: {profile.tone}")
        print(f"  Formality level: {profile.formality_level}/10")
        print(f"  Greeting style: '{profile.greeting_style}'")
        print(f"  Sign-off style: '{profile.sign_off_style}'")
        print(f"  Uses emojis: {profile.uses_emojis}")
        print(f"  Uses humor: {profile.uses_humor}")
        print(f"  Sentence length: {profile.sentence_length}")
        if profile.common_phrases:
            print(f"  Common phrases: {profile.common_phrases}")
        print("="*50 + "\n")
        
        assert profile is not None
        assert profile.writing_samples == writing_samples


@pytest.mark.online
class TestMessageGeneratorOnline:
    """Online tests for message generator agent."""

    def test_linkedin_dm_generation(self):
        """Test generating a LinkedIn DM."""
        print_header("LINKEDIN DM GENERATION TEST")
        
        print("Prospect: Sarah Chen, VP of Sales @ TechCorp")
        print("Trigger: Liked her post about SDR training challenges")
        print("Voice: Casual, formality 3/10")
        
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        message = crew.generate_message(SAMPLE_REQUEST)
        print_message(message, "LinkedIn DM")
        
        assert message.message is not None
        assert len(message.message) > 0
        assert message.message_type == MessageType.LINKEDIN_DM

    def test_connection_request_generation(self):
        """Test generating a connection request (300 char limit)."""
        print_header("CONNECTION REQUEST GENERATION TEST")
        
        print("Prospect: Sarah Chen, VP of Sales @ TechCorp")
        print("Constraint: 300 character limit")
        
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        request = SAMPLE_REQUEST.model_copy()
        request.message_type = MessageType.CONNECTION_REQUEST
        
        message = crew.generate_message(request)
        print_message(message, "Connection Request")
        
        if message.character_count > 300:
            print(f"⚠️  WARNING: Message exceeds 300 char limit ({message.character_count} chars)")
        else:
            print(f"✓ Within 300 char limit ({message.character_count} chars)")
        
        assert message.message is not None
        assert message.message_type == MessageType.CONNECTION_REQUEST

    def test_email_generation(self):
        """Test generating an email with subject line."""
        print_header("EMAIL GENERATION TEST")
        
        print("Prospect: Sarah Chen, VP of Sales @ TechCorp")
        print("Includes: Subject line")
        
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        request = SAMPLE_REQUEST.model_copy()
        request.message_type = MessageType.EMAIL
        
        message = crew.generate_message(request)
        print_message(message, "Email")
        
        assert message.message is not None
        assert message.message_type == MessageType.EMAIL


@pytest.mark.online
class TestOutreachCrewOnline:
    """Online tests for full outreach crew."""

    def test_generate_message_without_voice_profile(self):
        """Test generating message without pre-defined voice profile."""
        print_header("MESSAGE WITHOUT VOICE PROFILE TEST")
        
        print("Testing with default voice profile (no samples)")
        
        crew = OutreachMessageCrew(outreach_rules=SAMPLE_RULES)
        message = crew.generate_message(SAMPLE_REQUEST)
        
        print_message(message, "Default Voice Message")
        
        assert message.message is not None

    def test_generate_with_advanced_questions(self):
        """Test generating message with advanced questions context."""
        print_header("MESSAGE WITH ADVANCED QUESTIONS TEST")
        
        rules = OutreachRules(
            dos=["Reference their specific challenges"],
            donts=["Be generic"],
            advanced_questions=[
                AdvancedQuestion(
                    question="What's your unique selling point?",
                    answer="We reduce SDR ramp time from 3 months to 3 weeks using AI coaching"
                ),
                AdvancedQuestion(
                    question="What's your ideal customer profile?",
                    answer="Series A-C SaaS companies scaling their sales teams"
                ),
                AdvancedQuestion(
                    question="What objection do you hear most?",
                    answer="We already have a training program"
                ),
            ],
        )
        
        print("Advanced Questions provided:")
        for qa in rules.advanced_questions:
            print(f"  Q: {qa.question}")
            print(f"  A: {qa.answer}")
            print()
        
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=rules,
        )
        
        message = crew.generate_message(SAMPLE_REQUEST)
        print_message(message, "Message with Advanced Context")
        
        assert message.message is not None

    def test_generate_sequence(self):
        """Test generating a message sequence."""
        print_header("MESSAGE SEQUENCE GENERATION TEST")
        
        print("Generating 2-message sequence:")
        print("  1. Initial LinkedIn DM")
        print("  2. Follow-up message")
        
        crew = OutreachMessageCrew(
            voice_profile=SAMPLE_VOICE_PROFILE,
            outreach_rules=SAMPLE_RULES,
        )
        
        messages = crew.generate_sequence(SAMPLE_REQUEST, num_messages=2)
        
        for i, msg in enumerate(messages, 1):
            print_message(msg, f"Sequence Message {i} ({msg.message_type.value})")
        
        assert len(messages) == 2
        assert messages[0].message_type == MessageType.LINKEDIN_DM
        assert messages[1].message_type == MessageType.FOLLOW_UP
