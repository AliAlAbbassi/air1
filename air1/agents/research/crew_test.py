"""Unit tests for research crew."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from air1.agents.research.crew import ResearchProspectCrew
from air1.agents.research.models import ProspectInput, AISummary


class TestResearchProspectCrew:
    """Tests for ResearchProspectCrew class."""

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_init_creates_agents(
        self,
        mock_ai_summary,
        mock_icp,
        mock_talking,
        mock_pain,
        mock_company,
        mock_linkedin,
    ):
        """Test that initialization creates all agents."""
        crew = ResearchProspectCrew(product_context="B2B SaaS")
        
        assert crew.product_context == "B2B SaaS"
        mock_linkedin.assert_called_once()
        mock_company.assert_called_once()
        mock_pain.assert_called_once()
        mock_talking.assert_called_once()
        mock_icp.assert_called_once()
        mock_ai_summary.assert_called_once()

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_init_default_product_context(
        self,
        mock_ai_summary,
        mock_icp,
        mock_talking,
        mock_pain,
        mock_company,
        mock_linkedin,
    ):
        """Test default product context is empty string."""
        crew = ResearchProspectCrew()
        assert crew.product_context == ""


class TestParseAISummary:
    """Tests for _parse_ai_summary method."""

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_parse_complete_summary(self, *mocks):
        """Test parsing a complete AI summary."""
        crew = ResearchProspectCrew()
        
        raw_output = """
PROSPECT SUMMARY
John Doe is a seasoned VP of Sales with over 10 years of experience in B2B SaaS.
He has a track record of building high-performing sales teams.

COMPANY SUMMARY
Acme Inc is a fast-growing B2B SaaS company focused on sales automation.
They recently raised Series B funding.

NOTABLE ACHIEVEMENTS IN CURRENT ROLE
- Grew sales team from 5 to 25 people
- Increased ARR by 300% in 2 years
- Launched enterprise sales motion

OTHER NOTABLE ACHIEVEMENTS
- Founded a successful startup (acquired)
- Speaker at SaaStr Annual

RELEVANCY TO YOU
John is an ideal prospect because he's actively scaling his sales team
and looking for automation tools.

KEY TALKING POINTS
- Recent team growth challenges
- Interest in AI-powered tools
- Focus on enterprise deals

POTENTIAL PAIN POINTS
- Manual lead qualification
- Scaling outbound processes
- Rep productivity

RECOMMENDED APPROACH
Reach out via LinkedIn with a personalized message referencing his recent post about AI.
"""
        
        result = crew._parse_ai_summary(raw_output)
        
        assert result is not None
        assert "John Doe" in result.prospect_summary
        assert "Acme Inc" in result.company_summary
        assert len(result.notable_achievements_current_role) >= 2
        assert len(result.other_notable_achievements) >= 1
        assert "ideal prospect" in result.relevancy_to_you
        assert len(result.key_talking_points) >= 2
        assert len(result.potential_pain_points) >= 2
        assert "LinkedIn" in result.recommended_approach

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_parse_minimal_summary(self, *mocks):
        """Test parsing a minimal AI summary."""
        crew = ResearchProspectCrew()
        
        raw_output = """
PROSPECT SUMMARY
John is a sales leader.

COMPANY SUMMARY
Acme is a tech company.

RELEVANCY TO YOU
Good fit for our product.
"""
        
        result = crew._parse_ai_summary(raw_output)
        
        assert result is not None
        assert "John" in result.prospect_summary
        assert "Acme" in result.company_summary
        assert result.notable_achievements_current_role == []

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_parse_empty_output(self, *mocks):
        """Test parsing empty output returns None."""
        crew = ResearchProspectCrew()
        
        result = crew._parse_ai_summary("")
        assert result is None

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_parse_no_sections(self, *mocks):
        """Test parsing output with no recognized sections."""
        crew = ResearchProspectCrew()
        
        raw_output = "Just some random text without any sections."
        result = crew._parse_ai_summary(raw_output)
        assert result is None

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_parse_bullet_formats(self, *mocks):
        """Test parsing different bullet point formats."""
        crew = ResearchProspectCrew()
        
        raw_output = """
PROSPECT SUMMARY
Test prospect.

COMPANY SUMMARY
Test company.

RELEVANCY TO YOU
Relevant.

KEY TALKING POINTS
- Dash bullet
• Circle bullet
* Star bullet
1. Numbered item
2. Another numbered

POTENTIAL PAIN POINTS
- Pain 1
- Pain 2
"""
        
        result = crew._parse_ai_summary(raw_output)
        
        assert result is not None
        assert len(result.key_talking_points) >= 4
        assert len(result.potential_pain_points) >= 2


class TestResearchProspectsBatch:
    """Tests for research_prospects_batch method."""

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_batch_handles_errors(self, *mocks):
        """Test batch processing handles individual errors gracefully."""
        crew = ResearchProspectCrew()
        
        # Mock research_prospect to fail on second call
        with patch.object(crew, "research_prospect") as mock_research:
            from air1.agents.research.models import ResearchOutput
            
            prospect1 = ProspectInput(linkedin_username="user1")
            prospect2 = ProspectInput(linkedin_username="user2")
            prospect3 = ProspectInput(linkedin_username="user3")
            
            mock_research.side_effect = [
                ResearchOutput(prospect=prospect1, raw_research={"success": True}),
                Exception("API Error"),
                ResearchOutput(prospect=prospect3, raw_research={"success": True}),
            ]
            
            results = crew.research_prospects_batch([prospect1, prospect2, prospect3])
            
            assert len(results) == 3
            assert results[0].raw_research.get("success") is True
            assert "error" in results[1].raw_research
            assert results[2].raw_research.get("success") is True

    @patch("air1.agents.research.crew.create_linkedin_researcher")
    @patch("air1.agents.research.crew.create_company_researcher")
    @patch("air1.agents.research.crew.create_pain_point_analyst")
    @patch("air1.agents.research.crew.create_talking_points_generator")
    @patch("air1.agents.research.crew.create_icp_scorer")
    @patch("air1.agents.research.crew.create_ai_summary_generator")
    def test_batch_empty_list(self, *mocks):
        """Test batch with empty list returns empty list."""
        crew = ResearchProspectCrew()
        
        results = crew.research_prospects_batch([])
        assert results == []
