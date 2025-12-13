"""Company Finder Agent Models.

Pydantic models for the company finder agent input/output.
"""

from pydantic import BaseModel, Field


class TargetCompanyProfile(BaseModel):
    """Profile defining what kind of companies to find on LinkedIn."""

    business_model: str = Field(
        ..., description="Business model type, e.g., 'software agency', 'SaaS company'"
    )
    service_description: str = Field(
        ..., description="Description of services/products they offer"
    )

    # Size criteria
    min_employees: int | None = Field(
        None, ge=1, description="Minimum company size (employees)"
    )
    max_employees: int | None = Field(
        None, ge=1, description="Maximum company size (employees)"
    )

    # LinkedIn filters
    industries: list[str] = Field(
        default_factory=list,
        description="LinkedIn industry filters, e.g., 'IT Services and IT Consulting'",
    )

    # Location criteria
    locations: list[str] | None = Field(
        None, description="Target locations. None means any location."
    )

    # Search guidance
    keywords: list[str] = Field(
        default_factory=list, description="Keywords to search for"
    )
    exclude_keywords: list[str] = Field(
        default_factory=list, description="Keywords to avoid/exclude"
    )

    # Context for AI understanding
    example_about_sections: list[str] = Field(
        default_factory=list,
        description="Example 'About' sections from ideal target companies",
    )
    detailed_criteria: str = Field(
        default="",
        description="Detailed description of ideal company characteristics",
    )
    buying_signals: list[str] = Field(
        default_factory=list,
        description="Buying signals/triggers to look for, e.g., 'Series A funding', 'Filed 10-K'",
    )

    # Search limits
    max_results: int = Field(
        default=50, ge=1, le=500, description="Maximum number of companies to find"
    )


class FoundCompany(BaseModel):
    """A company found by the agent."""

    company_name: str = Field(..., description="Company name")
    linkedin_username: str = Field(
        ..., description="LinkedIn company username, e.g., 'aiapexhealth'"
    )
    linkedin_url: str = Field(..., description="Full LinkedIn company URL")
    industry: str | None = Field(None, description="Company industry")
    description: str | None = Field(None, description="Company description/about")
    website: str | None = Field(None, description="Company website URL")
    match_score: int = Field(
        ..., ge=0, le=100, description="Relevance score 0-100"
    )
    match_reasoning: str = Field(
        ..., description="Why this company matches the target profile"
    )
    detected_signals: list[str] = Field(
        default_factory=list, description="List of detected buying signals"
    )


class CompanyFinderOutput(BaseModel):
    """Complete output from the company finder crew."""

    target_profile: TargetCompanyProfile = Field(
        ..., description="The target profile used for search"
    )
    companies: list[FoundCompany] = Field(
        default_factory=list, description="List of found companies"
    )
    search_queries_used: list[str] = Field(
        default_factory=list, description="Search queries that were executed"
    )
    total_found: int = Field(default=0, description="Total number of companies found")
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered during search"
    )
