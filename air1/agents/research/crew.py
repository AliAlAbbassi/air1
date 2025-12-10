"""Research Prospect Crew - orchestrates research agents."""

from crewai import Crew, Process
from loguru import logger

from air1.agents.research.agents import (
    create_linkedin_researcher,
    create_company_researcher,
    create_pain_point_analyst,
    create_talking_points_generator,
    create_icp_scorer,
    create_ai_summary_generator,
)
from air1.agents.research.tasks import (
    create_linkedin_research_task,
    create_company_research_task,
    create_pain_point_analysis_task,
    create_talking_points_task,
    create_icp_scoring_task,
    create_ai_summary_task,
)
from air1.agents.research.models import ProspectInput, ResearchOutput, AISummary, ICPProfile


class ResearchProspectCrew:
    """
    Research Prospect Crew that tracks custom buying signals across 60+ data points.
    
    This crew orchestrates multiple specialized agents to:
    1. Research LinkedIn profiles and activity
    2. Gather company intelligence
    3. Analyze pain points
    4. Generate personalized talking points
    5. Score prospects against ICP criteria
    """
    
    def __init__(self, icp_profile: ICPProfile | None = None):
        """
        Initialize the research crew.
        
        Args:
            icp_profile: Ideal Customer Profile to score prospects against
        """
        self.icp_profile = icp_profile or ICPProfile()
        self._setup_agents()
    
    def _setup_agents(self):
        """Initialize all agents."""
        self.linkedin_researcher = create_linkedin_researcher()
        self.company_researcher = create_company_researcher()
        self.pain_point_analyst = create_pain_point_analyst()
        self.talking_points_generator = create_talking_points_generator()
        self.icp_scorer = create_icp_scorer()
        self.ai_summary_generator = create_ai_summary_generator()
    
    def research_prospect(self, prospect: ProspectInput) -> ResearchOutput:
        """
        Run full research on a single prospect.
        
        Args:
            prospect: The prospect to research
            
        Returns:
            Complete research output including scores and talking points
        """
        logger.info(f"Starting research for prospect: {prospect.linkedin_username}")
        
        # Create tasks
        linkedin_task = create_linkedin_research_task(
            self.linkedin_researcher, prospect
        )
        
        company_task = create_company_research_task(
            self.company_researcher, 
            prospect.company_name or "Unknown Company"
        )
        
        pain_point_task = create_pain_point_analysis_task(
            self.pain_point_analyst,
            prospect,
            linkedin_task,
            company_task,
        )
        
        talking_points_task = create_talking_points_task(
            self.talking_points_generator,
            prospect,
            linkedin_task,
            company_task,
            pain_point_task,
        )
        
        icp_task = create_icp_scoring_task(
            self.icp_scorer,
            prospect,
            self.icp_profile,
            linkedin_task,
            company_task,
            pain_point_task,
        )
        
        # AI Summary task - the main output
        ai_summary_task = create_ai_summary_task(
            self.ai_summary_generator,
            prospect,
            self.icp_profile,
            linkedin_task,
            company_task,
            pain_point_task,
        )
        
        # Create and run crew
        crew = Crew(
            agents=[
                self.linkedin_researcher,
                self.company_researcher,
                self.pain_point_analyst,
                self.talking_points_generator,
                self.icp_scorer,
                self.ai_summary_generator,
            ],
            tasks=[
                linkedin_task,
                company_task,
                pain_point_task,
                talking_points_task,
                icp_task,
                ai_summary_task,
            ],
            process=Process.sequential,
            verbose=True,
        )
        
        result = crew.kickoff()
        
        logger.info(f"Research completed for: {prospect.linkedin_username}")
        
        # Parse AI summary from result
        ai_summary = self._parse_ai_summary(str(result))
        
        # Build output
        return ResearchOutput(
            prospect=prospect,
            ai_summary=ai_summary,
            raw_research={"crew_output": str(result)},
        )
    
    def research_prospects_batch(
        self, 
        prospects: list[ProspectInput],
    ) -> list[ResearchOutput]:
        """
        Research multiple prospects.
        
        Args:
            prospects: List of prospects to research
            
        Returns:
            List of research outputs
        """
        results = []
        for prospect in prospects:
            try:
                result = self.research_prospect(prospect)
                results.append(result)
            except Exception as e:
                logger.error(f"Error researching {prospect.linkedin_username}: {e}")
                results.append(ResearchOutput(
                    prospect=prospect,
                    raw_research={"error": str(e)},
                ))
        return results
    
    def _parse_ai_summary(self, raw_output: str) -> AISummary | None:
        """
        Parse the AI summary from crew output.
        
        This is a simple parser - in production you'd want structured output.
        """
        try:
            # Extract sections from the raw output
            sections = {
                "prospect_summary": "",
                "company_summary": "",
                "notable_achievements_current_role": [],
                "other_notable_achievements": [],
                "relevancy_to_you": "",
                "key_talking_points": [],
                "potential_pain_points": [],
                "recommended_approach": "",
            }
            
            # Simple extraction - look for section headers
            current_section = None
            lines = raw_output.split("\n")
            
            for line in lines:
                line_lower = line.lower().strip()
                
                if "prospect summary" in line_lower:
                    current_section = "prospect_summary"
                elif "company summary" in line_lower:
                    current_section = "company_summary"
                elif "notable achievements in current role" in line_lower:
                    current_section = "notable_achievements_current_role"
                elif "other notable achievements" in line_lower:
                    current_section = "other_notable_achievements"
                elif "relevancy to you" in line_lower or "relevancy" in line_lower:
                    current_section = "relevancy_to_you"
                elif "key talking points" in line_lower or "talking points" in line_lower:
                    current_section = "key_talking_points"
                elif "potential pain points" in line_lower or "pain points" in line_lower:
                    current_section = "potential_pain_points"
                elif "recommended approach" in line_lower:
                    current_section = "recommended_approach"
                elif current_section and line.strip():
                    # Add content to current section
                    if isinstance(sections[current_section], list):
                        # For list sections, look for bullet points or continuation
                        stripped = line.strip()
                        if stripped.startswith(("-", "•", "*")) or (
                            len(stripped) > 1 and stripped[0].isdigit() and stripped[1] in ".)"
                        ):
                            # New bullet point
                            item = stripped.lstrip("-•*0123456789.) ")
                            if item:
                                sections[current_section].append(item)
                        elif sections[current_section]:
                            # Continuation of previous item (multi-line content)
                            sections[current_section][-1] += " " + stripped
                        else:
                            # First item without bullet marker
                            sections[current_section].append(stripped)
                    else:
                        # For text sections, append
                        sections[current_section] += line.strip() + " "
            
            # Clean up text sections
            for key in ["prospect_summary", "company_summary", "relevancy_to_you", "recommended_approach"]:
                sections[key] = sections[key].strip()
            
            # Only return if we got meaningful content
            if sections["prospect_summary"] or sections["company_summary"]:
                return AISummary(**sections)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse AI summary: {e}")
            return None
    
    def quick_research(self, prospect: ProspectInput) -> ResearchOutput:
        """
        Run quick research (LinkedIn + pain points only).
        
        Args:
            prospect: The prospect to research
            
        Returns:
            Research output with LinkedIn and pain point analysis
        """
        logger.info(f"Starting quick research for: {prospect.linkedin_username}")
        
        linkedin_task = create_linkedin_research_task(
            self.linkedin_researcher, prospect
        )
        
        pain_point_task = create_pain_point_analysis_task(
            self.pain_point_analyst,
            prospect,
            linkedin_task,
            linkedin_task,  # Use linkedin as company context for quick mode
        )
        
        crew = Crew(
            agents=[self.linkedin_researcher, self.pain_point_analyst],
            tasks=[linkedin_task, pain_point_task],
            process=Process.sequential,
            verbose=True,
        )
        
        result = crew.kickoff()
        
        return ResearchOutput(
            prospect=prospect,
            raw_research={"crew_output": str(result)},
        )
