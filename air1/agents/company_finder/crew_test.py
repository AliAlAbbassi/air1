"""Unit tests for Company Finder Crew."""

import json
from unittest.mock import MagicMock, patch

import pytest

from air1.agents.company_finder.crew import CompanyFinderCrew
from air1.agents.company_finder.models import TargetCompanyProfile


class TestCompanyFinderCrew:
    @pytest.fixture
    def mock_crew_kickoff(self):
        with patch("air1.agents.company_finder.crew.Crew.kickoff") as mock:
            yield mock

    @pytest.fixture
    def mock_dependencies(self):
        # Patch create_llm to avoid API Key errors
        with patch("crewai.agent.core.create_llm") as mock_create_llm, \
             patch("air1.agents.company_finder.agents.get_llm") as mock_get_llm:
            
            mock_create_llm.return_value = MagicMock()
            mock_get_llm.return_value = "openai/gpt-3.5-turbo"
            
            yield (mock_create_llm, mock_get_llm)

    def test_find_companies_success(self, mock_crew_kickoff, mock_dependencies):
        """Test successful execution and parsing of company finder crew."""
        
        # Mock the crew output (LLM response)
        mock_output = [
            {
                "Company Name": "Acme Corp",
                "LinkedIn URL": "https://www.linkedin.com/company/acme-corp",
                "Match Score": 95,
                "Reasoning": "Perfect match for business model.",
                "Detected Signals": ["Series A funding", "Hiring Engineers"],
                "Extracted Details": {
                    "Industry": "Software",
                    "Website": "https://acme.com",
                    "Description": "Acme is a leading software provider."
                }
            }
        ]
        # Simulate Crew output
        mock_crew_kickoff.return_value = f"```json\n{json.dumps(mock_output)}\n```"

        target = TargetCompanyProfile(
            business_model="Software",
            service_description="SaaS",
            industries=["Tech"],
            keywords=["AI"],
            buying_signals=["Funding"]
        )

        crew = CompanyFinderCrew()
        result = crew.find_companies(target)

        # Verify output parsing
        assert len(result.companies) == 1
        company = result.companies[0]
        assert company.company_name == "Acme Corp"
        assert company.linkedin_username == "acme-corp"
        assert company.match_score == 95
        assert "Series A funding" in company.detected_signals
        assert result.total_found == 1
        assert not result.errors

    def test_find_companies_parse_error(self, mock_crew_kickoff, mock_dependencies):
        """Test handling of malformed output."""
        
        mock_crew_kickoff.return_value = "This is not JSON."
        
        target = TargetCompanyProfile(
            business_model="Software",
            service_description="SaaS"
        )

        crew = CompanyFinderCrew()
        result = crew.find_companies(target)

        assert len(result.companies) == 0
        assert len(result.errors) > 0
        assert "Parse error" in result.errors[0]
