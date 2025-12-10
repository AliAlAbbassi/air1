"""Pydantic models for research prospecting agents."""

from pydantic import BaseModel, Field
from typing import Optional


class ProspectInput(BaseModel):
    """Input model for prospect research."""
    
    linkedin_username: str = Field(..., description="LinkedIn username/handle")
    full_name: Optional[str] = Field(None, description="Full name of the prospect")
    headline: Optional[str] = Field(None, description="LinkedIn headline")
    company_name: Optional[str] = Field(None, description="Current company name")
    location: Optional[str] = Field(None, description="Location")


class PainPoint(BaseModel):
    """A single pain point identified for a prospect."""
    
    description: str = Field(..., description="Description of the pain point")
    intensity: int = Field(..., ge=1, le=10, description="Pain intensity score 1-10")
    evidence: str = Field(..., description="Evidence/reasoning for this pain point")
    urgency_trigger: Optional[str] = Field(None, description="Any trigger event creating urgency")


class TalkingPoint(BaseModel):
    """A personalized talking point for outreach."""
    
    point: str = Field(..., description="The talking point/conversation starter")
    research_backing: str = Field(..., description="The research supporting this point")
    value_transition: str = Field(..., description="How to transition to value prop")
    tone: str = Field(default="professional", description="Recommended tone")


class ICPScore(BaseModel):
    """ICP scoring for a prospect."""
    
    overall: int = Field(..., ge=0, le=100, description="Overall ICP fit score")
    problem_intensity: int = Field(..., ge=0, le=100, description="Problem intensity score")
    relevance: int = Field(..., ge=0, le=100, description="Product relevance score")
    likelihood_to_respond: int = Field(..., ge=0, le=100, description="Response likelihood score")
    reasoning: str = Field(..., description="Reasoning for the scores")
    recommendation: str = Field(..., description="pursue/nurture/skip")


class LinkedInActivity(BaseModel):
    """LinkedIn activity analysis."""
    
    recent_posts: list[str] = Field(default_factory=list, description="Recent post summaries")
    engagement_topics: list[str] = Field(default_factory=list, description="Topics they engage with")
    posting_frequency: str = Field(default="unknown", description="How often they post")
    engagement_style: str = Field(default="unknown", description="How they engage (comments, likes, shares)")


class CompanyIntelligence(BaseModel):
    """Company intelligence report."""
    
    company_name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    recent_funding: Optional[str] = None
    recent_news: list[str] = Field(default_factory=list)
    hiring_signals: list[str] = Field(default_factory=list)
    growth_indicators: list[str] = Field(default_factory=list)


class AISummary(BaseModel):
    """
    AI Summary for a prospect - Valley-style comprehensive overview.
    
    This is the main output that provides deep prospect insights for
    sales meetings, email sequences, and phone calls.
    """
    
    prospect_summary: str = Field(
        ..., 
        description="Comprehensive summary of the prospect's professional background"
    )
    company_summary: str = Field(
        ..., 
        description="Summary of the prospect's current company"
    )
    notable_achievements_current_role: list[str] = Field(
        default_factory=list,
        description="Notable achievements in their current role"
    )
    other_notable_achievements: list[str] = Field(
        default_factory=list,
        description="Other notable achievements from their career"
    )
    relevancy_to_you: str = Field(
        ...,
        description="Why this prospect is relevant to your product/company"
    )
    
    # Additional insights
    key_talking_points: list[str] = Field(
        default_factory=list,
        description="Key talking points for outreach"
    )
    potential_pain_points: list[str] = Field(
        default_factory=list,
        description="Potential pain points your solution could address"
    )
    recommended_approach: str = Field(
        default="",
        description="Recommended approach for reaching out"
    )


class ResearchOutput(BaseModel):
    """Complete research output for a prospect."""
    
    prospect: ProspectInput
    ai_summary: Optional[AISummary] = Field(
        None, description="Valley-style AI summary for the prospect"
    )
    linkedin_activity: Optional[LinkedInActivity] = None
    company_intelligence: Optional[CompanyIntelligence] = None
    pain_points: list[PainPoint] = Field(default_factory=list)
    talking_points: list[TalkingPoint] = Field(default_factory=list)
    icp_score: Optional[ICPScore] = None
    raw_research: dict = Field(default_factory=dict, description="Raw research data")
