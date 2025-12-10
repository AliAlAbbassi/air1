"""Research Prospect Crew - orchestrates research agents."""

from crewai import Crew, Process
from loguru import logger

from air1.agents.research.agents import (
    create_linkedin_researcher,
    create_company_researcher,
    create_pain_point_analyst,
    create_talking_points_generator,
    create_icp_scorer,
)
from air1.agents.research.tasks import (
    create_linkedin_research_task,
    create_company_research_task,
    create_pain_point_analysis_task,
    create_talking_points_task,
    create_icp_scoring_task,
)
from air1.agents.research.models import ProspectInput, ResearchOutput


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
    
    def __init__(self, product_context: str = ""):
        """
        Initialize the research crew.
        
        Args:
            product_context: Description of the product/ICP for scoring
        """
        self.product_context = product_context
        self._setup_agents()
    
    def _setup_agents(self):
        """Initialize all agents."""
        self.linkedin_researcher = create_linkedin_researcher()
        self.company_researcher = create_company_researcher()
        self.pain_point_analyst = create_pain_point_analyst()
        self.talking_points_generator = create_talking_points_generator()
        self.icp_scorer = create_icp_scorer()
    
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
            self.product_context,
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
            ],
            tasks=[
                linkedin_task,
                company_task,
                pain_point_task,
                talking_points_task,
                icp_task,
            ],
            process=Process.sequential,
            verbose=True,
        )
        
        result = crew.kickoff()
        
        logger.info(f"Research completed for: {prospect.linkedin_username}")
        
        # Build output
        return ResearchOutput(
            prospect=prospect,
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
