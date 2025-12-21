"""Tasks for outreach message generation."""

from crewai import Agent, Task

from air1.agents.outreach.models import (
    VoiceProfile,
    OutreachRules,
    MessageRequest,
    MessageType,
)


def create_voice_analysis_task(
    agent: Agent,
    writing_samples: list[str],
) -> Task:
    """
    Task to analyze writing samples and extract voice characteristics.
    
    Args:
        agent: The voice analyzer agent
        writing_samples: List of user's writing samples
    """
    samples_text = "\n\n---\n\n".join(
        f"SAMPLE {i+1}:\n{sample}" 
        for i, sample in enumerate(writing_samples[:5])
    )
    
    return Task(
        description=f"""Analyze the following writing samples to extract the user's 
        unique voice and communication style.
        
        {samples_text}
        
        Identify and document:
        1. Overall tone (casual, professional, friendly, direct, etc.)
        2. Formality level (1-10 scale)
        3. Greeting patterns (how they start messages)
        4. Sign-off patterns (how they end messages)
        5. Common phrases or expressions they use
        6. Sentence structure (short/punchy vs long/detailed)
        7. Use of emojis, humor, or personal touches
        8. Vocabulary preferences
        9. Any unique stylistic quirks
        
        Be specific and provide examples from the samples.""",
        expected_output="""A detailed voice profile including:
        - Tone description
        - Formality level (1-10)
        - Greeting style with examples
        - Sign-off style with examples
        - List of common phrases
        - Sentence length preference
        - Notes on emoji/humor usage
        - Key stylistic patterns to replicate""",
        agent=agent,
    )


def create_message_generation_task(
    agent: Agent,
    request: MessageRequest,
    voice_profile: VoiceProfile,
    outreach_rules: OutreachRules,
) -> Task:
    """
    Task to generate a personalized outreach message.
    
    Args:
        agent: The message generator agent
        request: Message generation request with prospect context
        voice_profile: User's voice profile for style cloning
        outreach_rules: User's dos and don'ts
    """
    # Build context sections
    prospect_context = _build_prospect_context(request)
    product_context = _build_product_context(request)
    message_constraints = _build_message_constraints(request, outreach_rules)
    
    return Task(
        description=f"""Generate a personalized {request.message_type.value} message 
        for the following prospect.
        
        {prospect_context}
        
        {product_context}
        
        {message_constraints}
        
        **OUTREACH TRIGGER:** {request.outreach_trigger or "General prospecting"}
        
        **SEQUENCE STEP:** {request.sequence_step} of outreach sequence
        {_format_previous_messages(request.previous_messages)}
        
        Generate a message that:
        1. Opens with a personalized hook based on the research
        2. Demonstrates genuine understanding of their situation
        3. Naturally transitions to your value proposition
        4. Ends with a clear, low-friction call-to-action
        5. Sounds exactly like the user would write it (match their voice)
        
        The message should feel like a warm, relevant outreach - not a cold template.""",
        expected_output=f"""A complete {request.message_type.value} message including:
        - The full message text
        - Character count
        - List of personalization elements used
        - Subject line (if applicable)
        - Confidence score (0-100)
        - Brief reasoning for the approach
        - 2-3 alternative opening lines""",
        agent=agent,
    )


def create_message_review_task(
    agent: Agent,
    generated_message: str,
    request: MessageRequest,
    outreach_rules: OutreachRules,
) -> Task:
    """
    Task to review and improve a generated message.
    
    Args:
        agent: The message reviewer agent
        generated_message: The message to review
        request: Original message request for context
        outreach_rules: Rules to check against
    """
    rules_checklist = _build_rules_checklist(outreach_rules)
    
    return Task(
        description=f"""Review the following outreach message for quality and effectiveness.
        
        **MESSAGE TO REVIEW:**
        {generated_message}
        
        **PROSPECT:** {request.prospect_name} - {request.prospect_title} at {request.prospect_company}
        
        **MESSAGE TYPE:** {request.message_type.value}
        
        {rules_checklist}
        
        Evaluate the message on:
        1. **Authenticity** - Does it sound human-written or AI-generated?
        2. **Personalization** - Is the personalization natural or forced?
        3. **Value clarity** - Is the value proposition clear?
        4. **Length** - Is it appropriate for the platform?
        5. **CTA** - Is the call-to-action clear and low-friction?
        6. **Tone** - Does it match the intended voice?
        7. **Rules compliance** - Does it follow all dos/don'ts?
        
        Provide specific feedback and suggest improvements if needed.""",
        expected_output="""A review including:
        - Overall quality score (0-100)
        - Pass/fail on each evaluation criteria
        - Specific issues found (if any)
        - Suggested improvements
        - Revised message (if improvements needed)
        - Final recommendation (send as-is, revise, or rewrite)""",
        agent=agent,
    )


def _build_prospect_context(request: MessageRequest) -> str:
    """Build prospect context section."""
    sections = [
        "**PROSPECT CONTEXT:**",
        f"- Name: {request.prospect_name}",
    ]
    
    if request.prospect_title:
        sections.append(f"- Title: {request.prospect_title}")
    if request.prospect_company:
        sections.append(f"- Company: {request.prospect_company}")
    
    if request.prospect_summary:
        sections.append(f"\n**PROSPECT SUMMARY:**\n{request.prospect_summary}")
    
    if request.company_summary:
        sections.append(f"\n**COMPANY SUMMARY:**\n{request.company_summary}")
    
    if request.pain_points:
        points = "\n".join(f"- {p}" for p in request.pain_points)
        sections.append(f"\n**IDENTIFIED PAIN POINTS:**\n{points}")
    
    if request.talking_points:
        points = "\n".join(f"- {p}" for p in request.talking_points)
        sections.append(f"\n**SUGGESTED TALKING POINTS:**\n{points}")
    
    if request.relevancy:
        sections.append(f"\n**WHY THEY'RE RELEVANT:**\n{request.relevancy}")
    
    return "\n".join(sections)


def _build_product_context(request: MessageRequest) -> str:
    """Build product context section."""
    if not request.product_description and not request.value_proposition:
        return ""
    
    sections = ["**YOUR PRODUCT/SERVICE:**"]
    
    if request.product_description:
        sections.append(f"Description: {request.product_description}")
    
    if request.value_proposition:
        sections.append(f"Value Prop: {request.value_proposition}")
    
    return "\n".join(sections)


def _build_message_constraints(
    request: MessageRequest, 
    rules: OutreachRules
) -> str:
    """Build message constraints based on type and rules."""
    constraints = ["**MESSAGE CONSTRAINTS:**"]
    
    # Platform-specific limits
    char_limits = {
        MessageType.CONNECTION_REQUEST: 300,
        MessageType.LINKEDIN_DM: 8000,
        MessageType.INMAIL: 1900,
        MessageType.EMAIL: 5000,
        MessageType.FOLLOW_UP: 8000,
    }
    
    limit = rules.max_length or char_limits.get(request.message_type, 2000)
    constraints.append(f"- Maximum length: {limit} characters")
    
    if request.message_type == MessageType.CONNECTION_REQUEST:
        constraints.append("- Must be concise and compelling (connection requests are short)")
        constraints.append("- No subject line needed")
    elif request.message_type == MessageType.INMAIL:
        constraints.append("- Include a compelling subject line")
        constraints.append("- Can be more detailed than connection request")
    elif request.message_type == MessageType.EMAIL:
        constraints.append("- Include a compelling subject line")
        constraints.append("- Can include more context and detail")
    
    return "\n".join(constraints)


def _format_previous_messages(messages: list[str]) -> str:
    """Format previous messages in sequence."""
    if not messages:
        return ""
    
    formatted = ["\n**PREVIOUS MESSAGES IN SEQUENCE:**"]
    for i, msg in enumerate(messages, 1):
        formatted.append(f"Message {i}: {msg[:200]}...")
    
    return "\n".join(formatted)


def _build_rules_checklist(rules: OutreachRules) -> str:
    """Build rules checklist for review."""
    checklist = ["**RULES TO CHECK:**"]
    
    if rules.dos:
        checklist.append("Must include:")
        for do in rules.dos:
            checklist.append(f"  [ ] {do}")
    
    if rules.donts:
        checklist.append("Must NOT include:")
        for dont in rules.donts:
            checklist.append(f"  [ ] {dont}")
    
    if rules.banned_phrases:
        phrases = ", ".join(f"'{p}'" for p in rules.banned_phrases)
        checklist.append(f"Banned phrases to check: {phrases}")
    
    return "\n".join(checklist) if len(checklist) > 1 else ""
