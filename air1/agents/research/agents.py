"""Research prospecting agents definitions."""

from crewai import Agent, LLM

from air1.agents.research.tools import (
    linkedin_profile_tool,
    company_research_tool,
    news_search_tool,
    job_posting_tool,
)
from air1.config import settings


def get_llm() -> LLM:
    """
    Get the LLM instance for agents using Vertex AI.
    
    Requires:
    - GOOGLE_CLOUD_PROJECT env var or settings.google_cloud_project
    - GOOGLE_CLOUD_REGION env var or settings.google_cloud_region
    - Google Cloud credentials (GOOGLE_APPLICATION_CREDENTIALS or gcloud auth)
    """
    return LLM(
        model=f"vertex_ai/{settings.vertex_ai_model}",
        temperature=0.7,
        vertex_project=settings.google_cloud_project,
        vertex_location=settings.google_cloud_region,
    )


def create_linkedin_researcher() -> Agent:
    """
    Agent that researches LinkedIn profiles and activity.
    Analyzes recent posts, engagement patterns, and topics of interest.
    """
    return Agent(
        role="LinkedIn Profile Researcher",
        goal="Gather comprehensive LinkedIn profile data and activity patterns for prospects",
        backstory="""You are an expert at analyzing LinkedIn profiles and understanding 
        professional backgrounds. You excel at identifying key talking points, recent 
        activities, and engagement patterns that can be used for personalized outreach.""",
        tools=[linkedin_profile_tool],
        llm=get_llm(),
        verbose=True,
    )


def create_company_researcher() -> Agent:
    """
    Agent that researches companies.
    Finds funding rounds, product launches, job postings, and company news.
    """
    return Agent(
        role="Company Intelligence Researcher",
        goal="Gather comprehensive company intelligence including news, funding, and growth signals",
        backstory="""You are a business intelligence expert who specializes in tracking 
        company developments. You monitor funding rounds, product launches, hiring trends, 
        and market positioning to identify buying signals and conversation starters.""",
        tools=[company_research_tool, news_search_tool, job_posting_tool],
        llm=get_llm(),
        verbose=True,
    )


def create_pain_point_analyst() -> Agent:
    """
    Agent that analyzes and infers pain points.
    Uses role, industry, and company context to identify challenges.
    """
    return Agent(
        role="Pain Point Analyst",
        goal="Identify and articulate prospect pain points based on their role, industry, and company context",
        backstory="""You are a sales intelligence expert who understands the challenges 
        faced by different roles across industries. You can infer pain points from job 
        titles, company size, industry trends, and recent company developments.""",
        llm=get_llm(),
        verbose=True,
    )


def create_talking_points_generator() -> Agent:
    """
    Agent that generates personalized talking points.
    Creates conversation starters based on research findings.
    """
    return Agent(
        role="Talking Points Strategist",
        goal="Generate compelling, personalized talking points for sales outreach",
        backstory="""You are a master at crafting personalized conversation starters. 
        You synthesize research findings into actionable talking points that resonate 
        with prospects and create genuine connections.""",
        llm=get_llm(),
        verbose=True,
    )


def create_icp_scorer() -> Agent:
    """
    Agent that scores prospects against ICP criteria.
    Evaluates problem intensity, relevance, and likelihood to respond.
    """
    return Agent(
        role="ICP Scoring Analyst",
        goal="Score prospects on ICP fit, problem intensity, relevance, and likelihood to respond",
        backstory="""You are an expert at evaluating prospect fit against ideal customer 
        profiles. You analyze multiple data points to score prospects on their likelihood 
        to benefit from and respond to outreach.""",
        llm=get_llm(),
        verbose=True,
    )
