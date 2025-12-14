"""Company Finder Crew - orchestrates the company finding process."""

import json
from loguru import logger
from crewai import Crew, Process

from air1.agents.company_finder.agents import (
    create_search_strategy_agent,
    create_company_finder_agent,
    create_signal_analyst_agent,
    create_company_validator_agent,
)
from air1.agents.company_finder.models import (
    TargetCompanyProfile,
    CompanyFinderOutput,
    FoundCompany,
)
from air1.agents.company_finder.tasks import (
    create_search_strategy_task,
    create_company_search_task,
    create_signal_analysis_task,
    create_company_validation_task,
)


class CompanyFinderCrew:
    """
    Crew that finds companies on LinkedIn based on a target profile.
    """

    def __init__(self):
        self._setup_agents()

    def _setup_agents(self):
        """Initialize all agents."""
        self.search_strategy_agent = create_search_strategy_agent()
        self.company_finder_agent = create_company_finder_agent()
        self.signal_analyst_agent = create_signal_analyst_agent()
        self.company_validator_agent = create_company_validator_agent()

    def find_companies(self, target: TargetCompanyProfile) -> CompanyFinderOutput:
        """
        Run the crew to find companies.

        Args:
            target: The target company profile

        Returns:
            Structured output with found companies and metadata
        """
        logger.info(f"Starting company search for: {target.business_model}")

        # Create tasks
        strategy_task = create_search_strategy_task(self.search_strategy_agent, target)
        
        search_task = create_company_search_task(
            self.company_finder_agent, 
            strategy_task,
            max_results=target.max_results
        )
        
        signal_task = create_signal_analysis_task(
            self.signal_analyst_agent,
            search_task,
            target
        )
        
        validation_task = create_company_validation_task(
            self.company_validator_agent, 
            target, 
            search_task,
            signal_task
        )

        # Assemble Crew
        crew = Crew(
            agents=[
                self.search_strategy_agent,
                self.company_finder_agent,
                self.signal_analyst_agent,
                self.company_validator_agent,
            ],
            tasks=[strategy_task, search_task, signal_task, validation_task],
            process=Process.sequential,
            verbose=True,
        )

        # Execute
        result = crew.kickoff()
        
        # Parse results
        output = self._parse_crew_result(str(result), target)
        
        logger.info(f"Company search completed. Found {len(output.companies)} companies.")
        return output

    def _parse_crew_result(
        self, raw_result: str, target: TargetCompanyProfile
    ) -> CompanyFinderOutput:
        """
        Parse the text output from CrewAI into structured CompanyFinderOutput.
        
        This is a best-effort parser since CrewAI V1 returns string output.
        Ideally, we would use structured output from the last task, but for now
        we'll parse the text or assume the last task prints a JSON-like structure.
        """
        companies = []
        errors = []
        
        try:
            # Try to find JSON block first
            json_str = raw_result
            if "```json" in raw_result:
                json_str = raw_result.split("```json")[1].split("```")[0]
            elif "```" in raw_result:
                json_str = raw_result.split("```")[1].split("```")[0]
            
            data = json.loads(json_str)
            if isinstance(data, list):
                for item in data:
                    companies.append(
                        FoundCompany(
                            company_name=item.get("Company Name", "Unknown"),
                            linkedin_username=self._extract_username(item.get("LinkedIn URL", "")),
                            linkedin_url=item.get("LinkedIn URL", ""),
                            match_score=int(item.get("Match Score", 0)),
                            match_reasoning=item.get("Reasoning", ""),
                            industry=item.get("Extracted Details", {}).get("Industry"),
                            website=item.get("Extracted Details", {}).get("Website"),
                            description=item.get("Extracted Details", {}).get("Description"),
                            detected_signals=item.get("Detected Signals", []),
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed to parse JSON result: {e}")
            errors.append(f"Parse error: {str(e)}")

        return CompanyFinderOutput(
            target_profile=target,
            companies=companies,
            search_queries_used=[],  # Would need to extract from strategy task output
            total_found=len(companies),
            errors=errors,
        )

    def _extract_username(self, url: str) -> str:
        """Extract username from LinkedIn URL."""
        if "/company/" in url:
            return url.split("/company/")[1].strip("/").split("?")[0]
        return ""
