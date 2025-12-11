"""Unit tests for research agent tools."""

import pytest

from air1.agents.research.tools import (
    linkedin_profile_tool,
    company_research_tool,
    news_search_tool,
    job_posting_tool,
)


class TestLinkedInProfileTool:
    """Tests for LinkedIn profile research tool."""

    def test_tool_returns_string(self):
        """Test tool returns a string response."""
        result = linkedin_profile_tool.run("johndoe")
        assert isinstance(result, str)
        assert "johndoe" in result

    def test_tool_has_description(self):
        """Test tool has proper description."""
        assert linkedin_profile_tool.description is not None
        assert "LinkedIn" in linkedin_profile_tool.description


class TestCompanyResearchTool:
    """Tests for company research tool."""

    def test_tool_returns_string(self):
        """Test tool returns a string response."""
        result = company_research_tool.run("Acme Inc")
        assert isinstance(result, str)
        assert "Acme Inc" in result

    def test_tool_has_description(self):
        """Test tool has proper description."""
        assert company_research_tool.description is not None
        assert "company" in company_research_tool.description.lower()


class TestNewsSearchTool:
    """Tests for news search tool."""

    def test_tool_returns_string(self):
        """Test tool returns a string response."""
        result = news_search_tool.run("Acme Inc funding")
        assert isinstance(result, str)
        assert "Acme Inc funding" in result

    def test_tool_has_description(self):
        """Test tool has proper description."""
        assert news_search_tool.description is not None
        assert "news" in news_search_tool.description.lower()


class TestJobPostingTool:
    """Tests for job posting analysis tool."""

    def test_tool_returns_string(self):
        """Test tool returns a string response."""
        result = job_posting_tool.run("Acme Inc")
        assert isinstance(result, str)
        assert "Acme Inc" in result

    def test_tool_has_description(self):
        """Test tool has proper description."""
        assert job_posting_tool.description is not None
        assert "job" in job_posting_tool.description.lower()
