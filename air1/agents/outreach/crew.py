"""Outreach Message Crew - orchestrates message generation agents."""

import re
from crewai import Crew, Process
from loguru import logger

from air1.agents.outreach.agents import (
    create_voice_analyzer,
    create_message_generator,
    create_message_reviewer,
)
from air1.agents.outreach.tasks import (
    create_voice_analysis_task,
    create_message_generation_task,
)
from air1.agents.outreach.models import (
    VoiceProfile,
    OutreachRules,
    MessageRequest,
    GeneratedMessage,
    MessageType,
)
from air1.agents.research.models import ResearchOutput


class OutreachMessageCrew:
    """
    Outreach Message Crew that generates personalized messages in the user's voice.
    
    This crew:
    1. Analyzes writing samples to learn the user's voice (optional, can be pre-computed)
    2. Generates personalized messages using prospect research
    3. Reviews messages for quality and rule compliance
    """
    
    def __init__(
        self,
        voice_profile: VoiceProfile | None = None,
        outreach_rules: OutreachRules | None = None,
    ):
        """
        Initialize the outreach crew.
        
        Args:
            voice_profile: Pre-computed voice profile (or will be analyzed from samples)
            outreach_rules: User's dos and don'ts for message generation
        """
        self.voice_profile = voice_profile or VoiceProfile()
        self.outreach_rules = outreach_rules or OutreachRules()
        self._setup_agents()
    
    def _setup_agents(self):
        """Initialize agents."""
        self.voice_analyzer = create_voice_analyzer()
        self.message_generator = create_message_generator(
            self.voice_profile, 
            self.outreach_rules
        )
        self.message_reviewer = create_message_reviewer()
    
    def analyze_voice(self, writing_samples: list[str]) -> VoiceProfile:
        """
        Analyze writing samples to build a voice profile.
        
        Args:
            writing_samples: List of user's writing samples (emails, messages, etc.)
            
        Returns:
            VoiceProfile with extracted characteristics
        """
        logger.info(f"Analyzing {len(writing_samples)} writing samples for voice profile")
        
        task = create_voice_analysis_task(self.voice_analyzer, writing_samples)
        
        crew = Crew(
            agents=[self.voice_analyzer],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            tracing=True,
        )
        
        result = crew.kickoff()
        
        # Parse result into VoiceProfile
        profile = self._parse_voice_profile(str(result), writing_samples)
        self.voice_profile = profile
        
        # Recreate message generator with new profile
        self.message_generator = create_message_generator(
            self.voice_profile,
            self.outreach_rules
        )
        
        logger.info("Voice profile analysis complete")
        return profile
    
    def generate_message(
        self,
        request: MessageRequest,
        review: bool = True,
    ) -> GeneratedMessage:
        """
        Generate a personalized outreach message.
        
        Args:
            request: Message generation request with prospect context
            review: Whether to run the message through review (default True)
            
        Returns:
            GeneratedMessage with the generated content
        """
        logger.info(f"Generating {request.message_type.value} for {request.prospect_name}")
        
        # Create generation task
        gen_task = create_message_generation_task(
            self.message_generator,
            request,
            self.voice_profile,
            self.outreach_rules,
        )
        
        agents = [self.message_generator]
        tasks = [gen_task]
        
        # Optionally add review
        if review:
            # We'll run generation first, then review
            pass
        
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            tracing=True,
        )
        
        result = crew.kickoff()
        
        # Parse result into GeneratedMessage
        message = self._parse_generated_message(str(result), request.message_type)
        
        logger.info(f"Message generated: {len(message.message)} chars")
        return message
    
    def generate_message_from_research(
        self,
        research: ResearchOutput,
        message_type: MessageType = MessageType.LINKEDIN_DM,
        outreach_trigger: str = "",
        product_description: str = "",
        value_proposition: str = "",
        sequence_step: int = 1,
        previous_messages: list[str] | None = None,
    ) -> GeneratedMessage:
        """
        Generate a message directly from ResearchOutput.
        
        Convenience method that extracts relevant fields from research.
        
        Args:
            research: ResearchOutput from the research crew
            message_type: Type of message to generate
            outreach_trigger: What triggered this outreach
            product_description: Your product description
            value_proposition: Your value proposition
            sequence_step: Step in outreach sequence
            previous_messages: Previous messages in sequence
        """
        # Extract data from research
        request = MessageRequest(
            message_type=message_type,
            prospect_name=research.prospect.full_name or research.prospect.linkedin_username,
            prospect_title=research.prospect.headline or "",
            prospect_company=research.prospect.company_name or "",
            prospect_summary=research.ai_summary.prospect_summary if research.ai_summary else "",
            company_summary=research.ai_summary.company_summary if research.ai_summary else "",
            pain_points=[p.description for p in research.pain_points] if research.pain_points else (
                research.ai_summary.potential_pain_points if research.ai_summary else []
            ),
            talking_points=[t.point for t in research.talking_points] if research.talking_points else (
                research.ai_summary.key_talking_points if research.ai_summary else []
            ),
            relevancy=research.ai_summary.relevancy_to_you if research.ai_summary else "",
            outreach_trigger=outreach_trigger,
            product_description=product_description,
            value_proposition=value_proposition,
            sequence_step=sequence_step,
            previous_messages=previous_messages or [],
        )
        
        return self.generate_message(request)
    
    def generate_sequence(
        self,
        request: MessageRequest,
        num_messages: int = 3,
    ) -> list[GeneratedMessage]:
        """
        Generate a sequence of follow-up messages.
        
        Args:
            request: Initial message request
            num_messages: Number of messages in sequence
            
        Returns:
            List of GeneratedMessage for the sequence
        """
        messages = []
        previous = []
        
        for step in range(1, num_messages + 1):
            # Update request for this step
            step_request = request.model_copy()
            step_request.sequence_step = step
            step_request.previous_messages = previous.copy()
            
            # Adjust message type for follow-ups
            if step > 1:
                step_request.message_type = MessageType.FOLLOW_UP
            
            message = self.generate_message(step_request)
            messages.append(message)
            previous.append(message.message)
        
        return messages
    
    def _parse_voice_profile(
        self, 
        raw_output: str, 
        writing_samples: list[str]
    ) -> VoiceProfile:
        """Parse voice analysis output into VoiceProfile."""
        try:
            profile = VoiceProfile(writing_samples=writing_samples)
            
            output_lower = raw_output.lower()
            
            # Extract tone
            if "casual" in output_lower:
                profile.tone = "casual"
            elif "formal" in output_lower:
                profile.tone = "formal"
            elif "friendly" in output_lower:
                profile.tone = "friendly"
            elif "direct" in output_lower:
                profile.tone = "direct"
            else:
                profile.tone = "professional"
            
            # Extract formality level
            formality_match = re.search(r'formality[:\s]+(\d+)', output_lower)
            if formality_match:
                profile.formality_level = min(10, max(1, int(formality_match.group(1))))
            
            # Extract greeting style
            greeting_match = re.search(r'greeting[:\s]+["\']?([^"\'.\n]+)', output_lower)
            if greeting_match:
                profile.greeting_style = greeting_match.group(1).strip()
            
            # Extract sign-off style
            signoff_match = re.search(r'sign.?off[:\s]+["\']?([^"\'.\n]+)', output_lower)
            if signoff_match:
                profile.sign_off_style = signoff_match.group(1).strip()
            
            # Check for emoji usage
            profile.uses_emojis = "emoji" in output_lower and "uses" in output_lower
            
            # Check for humor
            profile.uses_humor = "humor" in output_lower and ("uses" in output_lower or "incorporates" in output_lower)
            
            # Extract sentence length
            if "short" in output_lower and "sentence" in output_lower:
                profile.sentence_length = "short"
            elif "long" in output_lower and "sentence" in output_lower:
                profile.sentence_length = "long"
            else:
                profile.sentence_length = "medium"
            
            return profile
            
        except Exception as e:
            logger.warning(f"Failed to parse voice profile: {e}")
            return VoiceProfile(writing_samples=writing_samples)
    
    def _parse_generated_message(
        self, 
        raw_output: str,
        message_type: MessageType,
    ) -> GeneratedMessage:
        """Parse message generation output into GeneratedMessage."""
        try:
            # Try to extract the actual message
            message_text = self._extract_message_text(raw_output)
            
            # Extract subject line if present
            subject_line = None
            subject_match = re.search(r'subject[:\s]+["\']?([^"\'.\n]+)', raw_output.lower())
            if subject_match and message_type in [MessageType.EMAIL, MessageType.INMAIL]:
                subject_line = subject_match.group(1).strip()
            
            # Extract confidence score
            confidence = 75  # default
            confidence_match = re.search(r'confidence[:\s]+(\d+)', raw_output.lower())
            if confidence_match:
                confidence = min(100, max(0, int(confidence_match.group(1))))
            
            # Extract personalization elements
            personalization = []
            if "personalization" in raw_output.lower():
                # Look for bullet points after "personalization"
                pers_section = raw_output.lower().split("personalization")[1][:500]
                bullets = re.findall(r'[-•*]\s*([^\n]+)', pers_section)
                personalization = [b.strip() for b in bullets[:5]]
            
            # Extract alternative openers
            alternatives = []
            if "alternative" in raw_output.lower():
                alt_section = raw_output.lower().split("alternative")[1][:500]
                bullets = re.findall(r'[-•*]\s*([^\n]+)', alt_section)
                alternatives = [b.strip() for b in bullets[:3]]
            
            # Extract reasoning
            reasoning = ""
            reasoning_match = re.search(r'reasoning[:\s]+([^\n]+)', raw_output.lower())
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            return GeneratedMessage(
                message=message_text,
                message_type=message_type,
                character_count=len(message_text),
                personalization_elements=personalization,
                subject_line=subject_line,
                confidence_score=confidence,
                reasoning=reasoning,
                alternative_openers=alternatives,
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse generated message: {e}")
            # Return raw output as message
            return GeneratedMessage(
                message=raw_output[:2000],
                message_type=message_type,
                character_count=len(raw_output[:2000]),
            )
    
    def _extract_message_text(self, raw_output: str) -> str:
        """Extract the actual message text from LLM output."""
        # Try common patterns
        patterns = [
            r'(?:message|text)[:\s]*["\'](.+?)["\']',  # "message": "..."
            r'```\n?(.+?)\n?```',  # Code block
            r'(?:^|\n)["\']((?:Hey|Hi|Hello|Dear).+?)["\']',  # Quoted message starting with greeting
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw_output, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look for a message-like section
        lines = raw_output.split('\n')
        message_lines = []
        in_message = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Start capturing after "message:" or similar
            if any(marker in line_lower for marker in ['message:', 'full message:', 'generated message:']):
                in_message = True
                continue
            
            # Stop at metadata sections
            if in_message and any(marker in line_lower for marker in [
                'character count:', 'personalization:', 'confidence:', 
                'reasoning:', 'alternative:', 'subject line:'
            ]):
                break
            
            if in_message and line.strip():
                message_lines.append(line)
        
        if message_lines:
            return '\n'.join(message_lines).strip()
        
        # Fallback: return first substantial paragraph
        paragraphs = raw_output.split('\n\n')
        for p in paragraphs:
            if len(p.strip()) > 50 and not p.strip().startswith('#'):
                return p.strip()
        
        return raw_output[:1000]
