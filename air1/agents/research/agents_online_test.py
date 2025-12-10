"""
Online tests for research agents - tests actual LLM calls.

Run with: uv run pytest air1/agents/research/agents_online_test.py --online -v -s

These tests require:
- GOOGLE_CLOUD_PROJECT env var set
- gcloud auth application-default login
"""

import pytest
from loguru import logger
from crewai import Task, Crew, Process

from air1.agents.research.agents import (
    create_linkedin_researcher,
    create_company_researcher,
    create_pain_point_analyst,
    create_talking_points_generator,
    create_icp_scorer,
    create_ai_summary_generator,
)
from air1.agents.research.models import ProspectInput, ICPProfile


# Sample test data
SAMPLE_PROSPECT = ProspectInput(
    linkedin_username="satyanadella",
    full_name="Satya Nadella",
    headline="Chairman and CEO at Microsoft",
    company_name="Microsoft",
    location="Redmond, Washington",
)

SAMPLE_ICP = ICPProfile(
    target_titles=["CEO", "CTO", "VP Engineering"],
    target_industries=["Technology", "SaaS", "Enterprise Software"],
    target_company_sizes=["1000+", "10000+"],
    target_seniority=["C-Level", "VP"],
    pain_points_we_solve=["Digital transformation", "Cloud migration", "AI adoption"],
    value_proposition="AI-powered enterprise solutions",
    product_description="Enterprise AI platform for automation",
)


@pytest.mark.online
class TestLinkedInResearcherOnline:
    """Online tests for LinkedIn researcher agent."""

    def test_linkedin_researcher_responds(self, caplog):
        """Test that LinkedIn researcher can process a task and return output."""
        agent = create_linkedin_researcher()
        
        task = Task(
            description=f"""
            Research the LinkedIn profile for: {SAMPLE_PROSPECT.linkedin_username}
            Name: {SAMPLE_PROSPECT.full_name}
            Headline: {SAMPLE_PROSPECT.headline}
            
            Provide a brief summary of their professional background.
            """,
            expected_output="A brief professional summary",
            agent=agent,
        )
        
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        
        logger.info("=" * 60)
        logger.info("LINKEDIN RESEARCHER OUTPUT:")
        logger.info("=" * 60)
        logger.info(str(result))
        logger.info("=" * 60)
        
        assert result is not None
        assert len(str(result)) > 50


@pytest.mark.online
class TestCompanyResearcherOnline:
    """Online tests for company researcher agent."""

    def test_company_researcher_responds(self, caplog):
        """Test that company researcher can process a task and return output."""
        agent = create_company_researcher()
        
        task = Task(
            description=f"""
            Research the company: {SAMPLE_PROSPECT.company_name}
            
            Provide a brief overview including:
            - What the company does
            - Recent news or developments
            - Industry position
            """,
            expected_output="A brief company overview",
            agent=agent,
        )
        
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        
        logger.info("=" * 60)
        logger.info("COMPANY RESEARCHER OUTPUT:")
        logger.info("=" * 60)
        logger.info(str(result))
        logger.info("=" * 60)
        
        assert result is not None
        assert len(str(result)) > 50


@pytest.mark.online
class TestPainPointAnalystOnline:
    """Online tests for pain point analyst agent."""

    def test_pain_point_analyst_responds(self, caplog):
        """Test that pain point analyst can process a task and return output."""
        agent = create_pain_point_analyst()
        
        task = Task(
            description=f"""
            Analyze potential pain points for:
            
            Name: {SAMPLE_PROSPECT.full_name}
            Role: {SAMPLE_PROSPECT.headline}
            Company: {SAMPLE_PROSPECT.company_name}
            
            What challenges might someone in this role face?
            List 3-5 potential pain points.
            """,
            expected_output="A list of 3-5 pain points with brief explanations",
            agent=agent,
        )
        
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        
        logger.info("=" * 60)
        logger.info("PAIN POINT ANALYST OUTPUT:")
        logger.info("=" * 60)
        logger.info(str(result))
        logger.info("=" * 60)
        
        assert result is not None
        assert len(str(result)) > 50


@pytest.mark.online
class TestTalkingPointsGeneratorOnline:
    """Online tests for talking points generator agent."""

    def test_talking_points_generator_responds(self, caplog):
        """Test that talking points generator can process a task and return output."""
        agent = create_talking_points_generator()
        
        task = Task(
            description=f"""
            Generate personalized talking points for outreach to:
            
            Name: {SAMPLE_PROSPECT.full_name}
            Role: {SAMPLE_PROSPECT.headline}
            Company: {SAMPLE_PROSPECT.company_name}
            
            Create 3 conversation starters that would resonate with this person.
            """,
            expected_output="3 personalized talking points",
            agent=agent,
        )
        
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        
        logger.info("=" * 60)
        logger.info("TALKING POINTS GENERATOR OUTPUT:")
        logger.info("=" * 60)
        logger.info(str(result))
        logger.info("=" * 60)
        
        assert result is not None
        assert len(str(result)) > 50


@pytest.mark.online
class TestICPScorerOnline:
    """Online tests for ICP scorer agent."""

    def test_icp_scorer_responds(self, caplog):
        """Test that ICP scorer can process a task and return output."""
        agent = create_icp_scorer()
        
        icp_details = f"""
        TARGET TITLES: {', '.join(SAMPLE_ICP.target_titles)}
        TARGET INDUSTRIES: {', '.join(SAMPLE_ICP.target_industries)}
        TARGET COMPANY SIZES: {', '.join(SAMPLE_ICP.target_company_sizes)}
        PRODUCT: {SAMPLE_ICP.product_description}
        """
        
        task = Task(
            description=f"""
            Score this prospect against the ICP:
            
            PROSPECT:
            Name: {SAMPLE_PROSPECT.full_name}
            Role: {SAMPLE_PROSPECT.headline}
            Company: {SAMPLE_PROSPECT.company_name}
            
            ICP CRITERIA:
            {icp_details}
            
            Provide scores (0-100) for:
            - Overall ICP Fit
            - Problem Intensity
            - Relevance
            - Likelihood to Respond
            
            And a recommendation: pursue/nurture/skip
            """,
            expected_output="ICP scores and recommendation",
            agent=agent,
        )
        
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        
        logger.info("=" * 60)
        logger.info("ICP SCORER OUTPUT:")
        logger.info("=" * 60)
        logger.info(str(result))
        logger.info("=" * 60)
        
        assert result is not None
        assert len(str(result)) > 50


@pytest.mark.online
class TestAISummaryGeneratorOnline:
    """Online tests for AI summary generator agent."""

    def test_ai_summary_generator_responds(self, caplog):
        """Test that AI summary generator can process a task and return output."""
        agent = create_ai_summary_generator()
        
        task = Task(
            description=f"""
            Generate a comprehensive AI Summary for:
            
            Name: {SAMPLE_PROSPECT.full_name}
            Role: {SAMPLE_PROSPECT.headline}
            Company: {SAMPLE_PROSPECT.company_name}
            Location: {SAMPLE_PROSPECT.location}
            
            Our Product: {SAMPLE_ICP.product_description}
            Value Proposition: {SAMPLE_ICP.value_proposition}
            
            Include:
            1. PROSPECT SUMMARY - Who they are professionally
            2. COMPANY SUMMARY - What their company does
            3. NOTABLE ACHIEVEMENTS - Key accomplishments
            4. RELEVANCY TO YOU - Why they're a good prospect
            5. KEY TALKING POINTS - Conversation starters
            6. RECOMMENDED APPROACH - How to reach out
            """,
            expected_output="A comprehensive AI summary with all sections",
            agent=agent,
        )
        
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        
        logger.info("=" * 60)
        logger.info("AI SUMMARY GENERATOR OUTPUT:")
        logger.info("=" * 60)
        logger.info(str(result))
        logger.info("=" * 60)
        
        assert result is not None
        assert len(str(result)) > 100


@pytest.mark.online
class TestFullResearchCrewOnline:
    """Online test for the full research crew."""

    def test_full_research_crew(self, caplog):
        """Test the complete research crew with all agents."""
        from air1.agents.research.crew import ResearchProspectCrew
        
        crew = ResearchProspectCrew(icp_profile=SAMPLE_ICP)
        result = crew.research_prospect(SAMPLE_PROSPECT)
        
        logger.info("=" * 60)
        logger.info("FULL RESEARCH CREW OUTPUT:")
        logger.info("=" * 60)
        logger.info(f"Prospect: {result.prospect.linkedin_username}")
        logger.info(f"Raw Research: {result.raw_research}")
        
        if result.ai_summary:
            logger.info("\nAI SUMMARY:")
            logger.info(f"Prospect Summary: {result.ai_summary.prospect_summary[:200]}...")
            logger.info(f"Company Summary: {result.ai_summary.company_summary[:200]}...")
            logger.info(f"Achievements: {result.ai_summary.notable_achievements_current_role}")
            logger.info(f"Talking Points: {result.ai_summary.key_talking_points}")
            logger.info(f"Recommended Approach: {result.ai_summary.recommended_approach}")
        
        logger.info("=" * 60)
        
        assert result is not None
        assert result.prospect.linkedin_username == SAMPLE_PROSPECT.linkedin_username
