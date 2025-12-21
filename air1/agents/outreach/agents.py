"""Outreach message generation agents."""

from crewai import Agent, LLM

from air1.config import settings
from air1.agents.outreach.models import VoiceProfile, OutreachRules


def get_llm() -> LLM:
    """Get the LLM instance for agents using Vertex AI."""
    return LLM(
        model=f"vertex_ai/{settings.vertex_ai_model}",
        temperature=0.7,
        vertex_project=settings.google_cloud_project,
        vertex_location=settings.google_cloud_region,
    )


def create_voice_analyzer() -> Agent:
    """
    Agent that analyzes writing samples to extract voice/style characteristics.
    
    This agent learns the user's unique communication style from their
    writing samples to enable authentic message generation.
    """
    return Agent(
        role="Voice & Style Analyzer",
        goal="Analyze writing samples to extract voice characteristics and communication style",
        backstory="""You are an expert linguist and communication analyst who specializes 
        in understanding individual writing styles. You can identify:
        
        - Tone and formality level
        - Sentence structure patterns
        - Common phrases and expressions
        - Greeting and sign-off preferences
        - Use of humor, emojis, and personal touches
        - Vocabulary choices and word preferences
        
        Your analysis enables other agents to generate messages that authentically 
        replicate the user's voice, making AI-generated messages indistinguishable 
        from ones the user would write themselves.""",
        llm=get_llm(),
        verbose=True,
    )


def create_message_generator(
    voice_profile: VoiceProfile | None = None,
    outreach_rules: OutreachRules | None = None,
) -> Agent:
    """
    Agent that generates personalized outreach messages in the user's voice.
    
    This is the core agent that:
    1. Takes prospect research insights
    2. Applies the user's voice/style
    3. Follows dos and don'ts rules
    4. Generates authentic, personalized messages
    
    Args:
        voice_profile: User's voice characteristics for style cloning
        outreach_rules: User's dos and don'ts for message generation
    """
    voice_profile = voice_profile or VoiceProfile()
    outreach_rules = outreach_rules or OutreachRules()
    
    # Build voice instructions
    voice_instructions = _build_voice_instructions(voice_profile)
    rules_instructions = _build_rules_instructions(outreach_rules)
    
    backstory = f"""You are an expert sales copywriter who specializes in crafting 
    hyper-personalized outreach messages. You excel at:
    
    1. **Voice Cloning**: Writing messages that sound exactly like the sender wrote them.
       You match their tone, vocabulary, sentence structure, and personality.
    
    2. **Research Integration**: Weaving prospect insights naturally into messages
       without being creepy or over-the-top. You reference specific details that
       show genuine interest without sounding like a stalker.
    
    3. **Value Communication**: Transitioning smoothly from personalization to
       value proposition without being salesy or pushy.
    
    4. **Platform Awareness**: Adapting message length and style for different
       platforms (LinkedIn connection requests are 300 chars, DMs can be longer).
    
    {voice_instructions}
    
    {rules_instructions}
    
    Your messages achieve high response rates because they feel genuine, relevant,
    and respectful of the prospect's time. You never use generic templates or
    obvious AI patterns."""
    
    return Agent(
        role="Outreach Message Generator",
        goal="Generate personalized outreach messages that sound authentically human and drive responses",
        backstory=backstory,
        llm=get_llm(),
        verbose=True,
    )


def create_message_reviewer() -> Agent:
    """
    Agent that reviews and improves generated messages.
    
    Acts as a quality gate to ensure messages meet standards before sending.
    """
    return Agent(
        role="Message Quality Reviewer",
        goal="Review messages for quality, authenticity, and effectiveness",
        backstory="""You are a senior sales leader who has reviewed thousands of 
        outreach messages. You have a keen eye for:
        
        - Messages that sound too AI-generated or templated
        - Personalization that feels forced or creepy
        - Value propositions that are unclear or too salesy
        - Messages that are too long or don't respect the prospect's time
        - Tone mismatches that could hurt response rates
        
        You provide specific, actionable feedback to improve messages and flag
        any issues that could hurt deliverability or response rates.""",
        llm=get_llm(),
        verbose=True,
    )


def _build_voice_instructions(voice_profile: VoiceProfile) -> str:
    """Build voice cloning instructions from profile."""
    if not voice_profile.writing_samples:
        return ""
    
    instructions = ["**USER'S VOICE PROFILE:**"]
    
    if voice_profile.tone:
        instructions.append(f"- Tone: {voice_profile.tone}")
    
    if voice_profile.formality_level:
        level_desc = {
            1: "very casual",
            2: "casual", 
            3: "somewhat casual",
            4: "slightly casual",
            5: "neutral",
            6: "slightly formal",
            7: "somewhat formal",
            8: "formal",
            9: "very formal",
            10: "extremely formal"
        }
        instructions.append(f"- Formality: {level_desc.get(voice_profile.formality_level, 'neutral')}")
    
    if voice_profile.greeting_style:
        instructions.append(f"- Greeting style: '{voice_profile.greeting_style}'")
    
    if voice_profile.sign_off_style:
        instructions.append(f"- Sign-off style: '{voice_profile.sign_off_style}'")
    
    if voice_profile.common_phrases:
        phrases = ", ".join(f"'{p}'" for p in voice_profile.common_phrases[:5])
        instructions.append(f"- Common phrases: {phrases}")
    
    if voice_profile.uses_emojis:
        instructions.append("- Uses emojis occasionally")
    
    if voice_profile.uses_humor:
        instructions.append("- Incorporates light humor")
    
    instructions.append(f"- Sentence length: {voice_profile.sentence_length}")
    
    if voice_profile.signature_opener:
        instructions.append(f"- Signature opener style: '{voice_profile.signature_opener}'")
    
    if voice_profile.personal_anecdotes:
        anecdotes = "; ".join(voice_profile.personal_anecdotes[:3])
        instructions.append(f"- Personal anecdotes to reference: {anecdotes}")
    
    if voice_profile.writing_samples:
        instructions.append("\n**WRITING SAMPLES TO EMULATE:**")
        for i, sample in enumerate(voice_profile.writing_samples[:3], 1):
            instructions.append(f"Sample {i}: \"{sample[:500]}\"")
    
    if voice_profile.instructions:
        instructions.append(f"\n**ADDITIONAL VOICE INSTRUCTIONS:**\n{voice_profile.instructions}")
    
    return "\n".join(instructions)


def _build_rules_instructions(rules: OutreachRules) -> str:
    """Build rules instructions from OutreachRules."""
    instructions = []
    
    if rules.dos:
        instructions.append("**DO:**")
        for do in rules.dos:
            instructions.append(f"- {do}")
    
    if rules.donts:
        instructions.append("\n**DON'T:**")
        for dont in rules.donts:
            instructions.append(f"- {dont}")
    
    if rules.banned_phrases:
        phrases = ", ".join(f"'{p}'" for p in rules.banned_phrases)
        instructions.append(f"\n**BANNED PHRASES:** {phrases}")
    
    if rules.always_mention:
        mentions = ", ".join(rules.always_mention)
        instructions.append(f"\n**ALWAYS MENTION (when relevant):** {mentions}")
    
    if rules.never_mention:
        mentions = ", ".join(rules.never_mention)
        instructions.append(f"\n**NEVER MENTION:** {mentions}")
    
    if rules.required_cta:
        instructions.append(f"\n**REQUIRED CTA STYLE:** {rules.required_cta}")
    
    if rules.max_length:
        instructions.append(f"\n**MAX LENGTH:** {rules.max_length} characters")
    
    if rules.instructions:
        instructions.append(f"\n**ADDITIONAL INSTRUCTIONS:**\n{rules.instructions}")
    
    if rules.advanced_questions:
        instructions.append("\n**USER CONTEXT (from Q&A):**")
        for qa in rules.advanced_questions[:5]:
            instructions.append(f"Q: {qa.question}")
            instructions.append(f"A: {qa.answer}")
    
    return "\n".join(instructions) if instructions else ""
