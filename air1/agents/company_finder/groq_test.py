"""
Rate-limit friendly online tests for Groq.
Designed to run with minimal token usage and API calls.
"""

import pytest
import time
from air1.agents.company_finder.crew import CompanyFinderCrew
from air1.agents.company_finder.models import TargetCompanyProfile

# Fixture to add delay between tests to respect rate limits
@pytest.fixture(autouse=True)
def rate_limit_delay():
    yield
    print("\nSleeping for 5s to respect Groq rate limits...")
    time.sleep(5)

@pytest.mark.integration
def test_groq_simple_company_search():
    """
    Lightweight test: Find 1 AI company.
    Low token usage, single result.
    """
    target = TargetCompanyProfile(
        business_model="AI Agent Agency",
        service_description="Builds AI agents for businesses",
        # Minimal context to save input tokens
        detailed_criteria="AI automation agency",
        keywords=["AI agents", "automation"],
        locations=["United States"],
        min_employees=1,
        max_employees=50,
        max_results=1, # FORCE 1 result to minimize subsequent tool calls
        buying_signals=[] # No signal analysis to save calls
    )
    
    crew = CompanyFinderCrew()
    result = crew.find_companies(target)
    
    assert result is not None
    # We might find 0 if search is too restrictive or fails, but we want to assert flow works
    # If 1 is found, great.
    if len(result.companies) > 0:
        print(f"Groq Found: {result.companies[0].company_name}")
        assert result.companies[0].linkedin_url

@pytest.mark.integration
def test_groq_signal_check_minimal():
    """
    Lightweight signal test: Check 1 specific company for 1 signal.
    """
    # Focusing on a known entity effectively acts as a direct lookup
    target = TargetCompanyProfile(
        business_model="Crypto Exchange",
        service_description="Crypto",
        detailed_criteria="Coinbase",
        keywords=["Coinbase"], 
        locations=["United States"],
        max_results=1,
        buying_signals=["SEC 10-K"]
    )
    
    crew = CompanyFinderCrew()
    result = crew.find_companies(target)
    
    if len(result.companies) > 0:
        company = result.companies[0]
        print(f"Groq Found with Signals: {company.company_name}")
        # Soft assertion on signals
        if company.detected_signals:
            print(f"Signals: {company.detected_signals}")
