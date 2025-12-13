"""Company Finder Agents."""

from crewai import Agent, LLM

from air1.agents.company_finder.tools import (
    crunchbase_search_tool,
    linkedin_company_info_tool,
    sec_filing_search_tool,
    web_search_tool,
)
from air1.config import settings


def get_llm() -> LLM:
    """Get the LLM instance for agents using Vertex AI (Gemini)."""
    return LLM(
        model=f"vertex_ai/{settings.vertex_ai_model}",
        temperature=0.7,
        vertex_project=settings.google_cloud_project,
        vertex_location=settings.google_cloud_region,
    )


def create_search_strategy_agent() -> Agent:
    """
    Agent that generates diverse search queries.
    """
    return Agent(
        role="Search Strategy Specialist",
        goal="Generate effective and diverse search queries to find niche companies on LinkedIn",
        backstory="""You are an expert at finding hard-to-reach companies using advanced search operators. 
        You understand how to translate business requirements into specific search queries that target 
        LinkedIn company pages, SEC filings, and Crunchbase profiles via search engines. 
        You know how to use 'site:linkedin.com/company/' combined with specific keywords.""",
        llm=get_llm(),
        verbose=True,
    )


def create_company_finder_agent() -> Agent:
    """
    Agent that executes searches and extracts company URLs.
    """
    return Agent(
        role="Company Researcher",
        goal="Find LinkedIn company pages matching the search criteria",
        backstory="""You are a diligent researcher who knows how to navigate search results 
        to find valid LinkedIn company pages. You can quickly distinguish between a company page, 
        a personal profile, or irrelevant noise. You are efficient at verifying if a URL 
        looks like the correct target.""",
        tools=[web_search_tool],
        llm=get_llm(),
        verbose=True,
    )


def create_signal_analyst_agent() -> Agent:
    """
    Agent that looks for buying signals.
    """
    return Agent(
        role="Buying Signal Analyst",
        goal="Identify buying signals (funding, filings, hiring) for candidate companies",
        backstory="""You are a financial analyst specializing in market intelligence. 
        Your job is to look for specific triggers that indicate a company is ready to buy. 
        You search for SEC filings (10-K, S-1), recent funding news on Crunchbase, 
        and other growth signals. You are precise in verifying if a signal belongs 
        to the correct company.""",
        tools=[sec_filing_search_tool, crunchbase_search_tool, web_search_tool],
        llm=get_llm(),
        verbose=True,
    )


def create_company_validator_agent() -> Agent:
    """
    Agent that validates companies against the target profile.
    """
    return Agent(
        role="Target Profile Validator",
        goal="Validate if a company strictly matches the Ideal Customer Profile (ICP) and has relevant signals",
        backstory="""You are a strict quality assurance analyst. Your job is to ensure 
        that only companies matching the detailed target criteria are accepted. 
        You analyze company descriptions, buying signals, and growth indicators 
        to score each prospect. You are not afraid to reject companies that don't match.""",
        tools=[linkedin_company_info_tool],
        llm=get_llm(),
        verbose=True,
    )
