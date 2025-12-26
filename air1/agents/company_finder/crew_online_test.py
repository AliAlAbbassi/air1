import pytest
from air1.agents.company_finder.crew import CompanyFinderCrew
from air1.agents.company_finder.models import TargetCompanyProfile

@pytest.mark.integration
def test_company_finder_air1_icp():
    """
    Online integration test that searches for companies matching Air1's ICP.
    
    Air1 ICP:
    - Fast-moving companies, Scale-ups
    - Need AI agents (Voice, Lead Qual, Workflow Automation)
    - Likely "Marketing Agencies", "SaaS", "Real Estate" (common for voice/lead agents)
    """
    
    # Define Target Profile based on Air1's landing page analysis
    target = TargetCompanyProfile(
        business_model="Marketing Agency or B2B SaaS",
        service_description="High volume sales or operational complexity suitable for automation",
        
        # Criteria
        min_employees=11,  # "Scale-ups" usually > 10
        max_employees=200, # Not enterprise bureaucracy
        
        # Limit scope for test
        max_results=2, 
        
        # Context
        detailed_criteria=(
            "Looking for companies that are likely to need AI automation for sales or operations. "
            "Fast-growing, modern tech stack or high-touch service businesses."
        ),
        
        keywords=["marketing agency", "software development", "real estate"],
        locations=["United States", "United Kingdom", "Canada"],  # English speaking primary
        
        buying_signals=[
            "hiring sales representatives",
            "active on linkedin", 
            "growing headcount"
        ]
    )
    
    # Initialize Crew
    crew = CompanyFinderCrew()
    
    # Execute Search
    result = crew.find_companies(target)
    
    
    # Assertions
    assert result is not None
    assert result.total_found >= 0
    
    # Check structure if companies are found
    if result.total_found > 0:
        company = result.companies[0]
        assert company.company_name
        assert company.linkedin_url
        assert company.match_score > 0
        
        print(f"\nFound {result.total_found} companies:")
        for c in result.companies:
            print(f"- {c.company_name} ({c.match_score}%): {c.linkedin_url}")
            print(f"  Reason: {c.match_reasoning}")
            print(f"  Signals: {c.detected_signals}")


@pytest.mark.integration
def test_company_finder_signals_sec():
    """
    Test specifically for SEC filing signals (e.g. Coinbase 10-K).
    """
    target = TargetCompanyProfile(
        business_model="Crypto Exchange",
        service_description="Cryptocurrency trading platform",
        min_employees=1000,
        max_employees=10000,
        locations=["United States"],
        keywords=["crypto", "exchange"],
        buying_signals=["SEC 10-K filing"], # Explicit signal for SEC tool
        max_results=1,
        detailed_criteria="Publicly traded crypto exchange."
    )
    
    crew = CompanyFinderCrew()
    result = crew.find_companies(target)
    
    if result.companies:
        company = result.companies[0]
        print(f"Found: {company.company_name}")
        print(f"Signals: {company.detected_signals}")
        # We expect some mention of filing or 10-K if the tool worked
        # Note: Search results depend on live web, so assertion is soft
        assert any("filing" in s.lower() or "10-k" in s.lower() for s in company.detected_signals), \
            f"Expected SEC filing signals, got: {company.detected_signals}"

