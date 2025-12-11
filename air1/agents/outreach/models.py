"""Pydantic models for outreach message generation."""

from enum import Enum
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Type of outreach message."""
    
    CONNECTION_REQUEST = "connection_request"  # LinkedIn connection request (300 char limit)
    LINKEDIN_DM = "linkedin_dm"  # LinkedIn direct message
    INMAIL = "inmail"  # LinkedIn InMail
    FOLLOW_UP = "follow_up"  # Follow-up message
    EMAIL = "email"  # Email outreach


class VoiceProfile(BaseModel):
    """
    User's voice/writing style profile for message cloning.
    
    Built from analyzing the user's past messages, emails, and writing samples.
    This enables generating messages that sound authentically like the user.
    """
    
    # Writing samples for style learning
    writing_samples: list[str] = Field(
        default_factory=list,
        description="Sample messages/emails written by the user for style learning"
    )
    
    # Extracted style characteristics
    tone: str = Field(
        default="professional",
        description="Overall tone (e.g., 'casual', 'professional', 'friendly', 'direct')"
    )
    formality_level: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Formality level 1-10 (1=very casual, 10=very formal)"
    )
    
    # Language patterns
    greeting_style: str = Field(
        default="",
        description="How they typically greet (e.g., 'Hey', 'Hi', 'Hello')"
    )
    sign_off_style: str = Field(
        default="",
        description="How they typically sign off (e.g., 'Best', 'Cheers', 'Thanks')"
    )
    common_phrases: list[str] = Field(
        default_factory=list,
        description="Phrases the user commonly uses"
    )
    
    # Style preferences
    uses_emojis: bool = Field(default=False, description="Whether they use emojis")
    uses_humor: bool = Field(default=False, description="Whether they use humor")
    sentence_length: str = Field(
        default="medium",
        description="Typical sentence length: 'short', 'medium', 'long'"
    )
    
    # Personal touches
    personal_anecdotes: list[str] = Field(
        default_factory=list,
        description="Personal stories/anecdotes they like to reference"
    )
    signature_opener: str = Field(
        default="",
        description="Their signature opening line style"
    )


class OutreachRules(BaseModel):
    """
    User-defined dos and don'ts for message generation.
    
    These rules constrain the AI to follow user preferences and avoid
    patterns that don't work for their specific context.
    """
    
    # Things to do
    dos: list[str] = Field(
        default_factory=list,
        description="Things to always include or do in messages"
    )
    
    # Things to avoid
    donts: list[str] = Field(
        default_factory=list,
        description="Things to never include or avoid in messages"
    )
    
    # Specific instructions
    always_mention: list[str] = Field(
        default_factory=list,
        description="Topics/points to always mention when relevant"
    )
    never_mention: list[str] = Field(
        default_factory=list,
        description="Topics/points to never mention"
    )
    
    # Banned words/phrases
    banned_phrases: list[str] = Field(
        default_factory=list,
        description="Specific phrases to never use (e.g., 'circle back', 'synergy')"
    )
    
    # Required elements
    required_cta: str = Field(
        default="",
        description="Required call-to-action style"
    )
    max_length: int | None = Field(
        default=None,
        description="Maximum message length in characters"
    )


class MessageRequest(BaseModel):
    """Request to generate an outreach message."""
    
    # Message type
    message_type: MessageType = Field(
        default=MessageType.LINKEDIN_DM,
        description="Type of message to generate"
    )
    
    # Prospect context (from ResearchOutput)
    prospect_name: str = Field(..., description="Prospect's name")
    prospect_title: str = Field(default="", description="Prospect's job title")
    prospect_company: str = Field(default="", description="Prospect's company")
    
    # Research insights to incorporate
    prospect_summary: str = Field(
        default="",
        description="AI summary of the prospect"
    )
    company_summary: str = Field(
        default="",
        description="AI summary of the prospect's company"
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description="Identified pain points"
    )
    talking_points: list[str] = Field(
        default_factory=list,
        description="Suggested talking points"
    )
    relevancy: str = Field(
        default="",
        description="Why prospect is relevant to your product"
    )
    
    # Trigger/context for outreach
    outreach_trigger: str = Field(
        default="",
        description="What triggered this outreach (e.g., 'liked your post about X', 'saw you're hiring')"
    )
    
    # Product context
    product_description: str = Field(
        default="",
        description="Description of your product/service"
    )
    value_proposition: str = Field(
        default="",
        description="Your value proposition"
    )
    
    # Sequence context
    sequence_step: int = Field(
        default=1,
        description="Which step in the outreach sequence (1=first touch)"
    )
    previous_messages: list[str] = Field(
        default_factory=list,
        description="Previous messages in the sequence for context"
    )


class GeneratedMessage(BaseModel):
    """Generated outreach message."""
    
    message: str = Field(..., description="The generated message")
    message_type: MessageType = Field(..., description="Type of message")
    
    # Metadata
    character_count: int = Field(..., description="Character count")
    personalization_elements: list[str] = Field(
        default_factory=list,
        description="Personalization elements used in the message"
    )
    
    # Variants
    subject_line: str | None = Field(
        default=None,
        description="Subject line (for emails/InMails)"
    )
    
    # Quality indicators
    confidence_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Confidence in message quality 0-100"
    )
    reasoning: str = Field(
        default="",
        description="Reasoning behind the message approach"
    )
    
    # Alternatives
    alternative_openers: list[str] = Field(
        default_factory=list,
        description="Alternative opening lines"
    )
