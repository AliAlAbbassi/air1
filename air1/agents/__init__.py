"""
CrewAI Agents for Air1.

This module contains AI agents built with CrewAI for:
- Research prospecting: Track custom buying signals across 60+ data points
- Sales agents: Outreach and engagement automation
- LinkedIn engagement: Track page engagements and generate AI outreach
"""

from air1.agents.research.crew import ResearchProspectCrew
from air1.agents.company_finder.crew import CompanyFinderCrew

__all__ = ["ResearchProspectCrew", "CompanyFinderCrew"]
