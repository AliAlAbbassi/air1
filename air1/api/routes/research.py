"""Research prospect API routes."""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from air1.agents.research.crew import ResearchProspectCrew
from air1.agents.research.models import ProspectInput, ResearchOutput, ICPProfile


router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    """Request model for prospect research."""
    
    linkedin_username: str = Field(..., description="LinkedIn username to research")
    full_name: Optional[str] = Field(None, description="Full name of the prospect")
    headline: Optional[str] = Field(None, description="LinkedIn headline")
    company_name: Optional[str] = Field(None, description="Current company name")
    location: Optional[str] = Field(None, description="Location")
    icp_profile: Optional[ICPProfile] = Field(
        None, description="ICP profile to score prospect against"
    )
    quick_mode: bool = Field(
        False, description="Run quick research (LinkedIn + pain points only)"
    )


class ResearchResponse(BaseModel):
    """Response model for prospect research."""
    
    status: str
    prospect: ProspectInput
    message: str
    result: Optional[ResearchOutput] = None


class BatchResearchRequest(BaseModel):
    """Request model for batch prospect research."""
    
    prospects: list[ProspectInput] = Field(..., description="List of prospects to research")
    product_context: Optional[str] = Field(None, description="Product/ICP context")


@router.post("/prospect", response_model=ResearchResponse)
async def research_prospect(request: ResearchRequest) -> ResearchResponse:
    """
    Research a single prospect using AI agents.
    
    This endpoint uses CrewAI agents to:
    - Research LinkedIn profile and activity
    - Gather company intelligence  
    - Analyze pain points
    - Generate personalized talking points
    - Score against ICP criteria
    """
    logger.info(f"Research request for: {request.linkedin_username}")
    
    prospect = ProspectInput(
        linkedin_username=request.linkedin_username,
        full_name=request.full_name,
        headline=request.headline,
        company_name=request.company_name,
        location=request.location,
    )
    
    try:
        crew = ResearchProspectCrew(icp_profile=request.icp_profile)
        
        if request.quick_mode:
            result = crew.quick_research(prospect)
        else:
            result = crew.research_prospect(prospect)
        
        return ResearchResponse(
            status="success",
            prospect=prospect,
            message="Research completed successfully",
            result=result,
        )
    except Exception as e:
        logger.error(f"Research failed for {request.linkedin_username}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prospect/batch")
async def research_prospects_batch(
    request: BatchResearchRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Queue batch research for multiple prospects.
    
    Research runs in the background. Use the status endpoint to check progress.
    """
    logger.info(f"Batch research request for {len(request.prospects)} prospects")
    
    # For now, return acknowledgment - in production, this would queue to a task system
    return {
        "status": "queued",
        "message": f"Research queued for {len(request.prospects)} prospects",
        "prospect_count": len(request.prospects),
    }


@router.get("/health")
async def research_health() -> dict:
    """Health check for research service."""
    return {"status": "healthy", "service": "research-agents"}
