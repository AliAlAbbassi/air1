"""LeadGen API routes.

All endpoints require a valid Clerk JWT token.
Searches are scoped to the authenticated user's clerk_id.
"""

from fastapi import APIRouter, Depends, HTTPException

from air1.api.auth import AuthUser, get_current_user
from air1.api.models.leadgen import (
    CreateSearchRequest,
    ErrorResponse,
    LeadResponse,
    SearchResponse,
    SearchResultsResponse,
    SearchStatsResponse,
    SoftwareProductResponse,
)
from air1.config import settings
from air1.services.leadgen.models import SearchParams
from air1.services.leadgen.patterns import BUILTIN_PATTERNS
from air1.services.leadgen.service import Service

router = APIRouter(prefix="/api/leadgen", tags=["leadgen"])


def _get_service() -> Service:
    return Service(serper_api_key=settings.serper_api_key)


# ---------------------------------------------------------------------------
# Software products
# ---------------------------------------------------------------------------


@router.get(
    "/software",
    response_model=list[SoftwareProductResponse],
)
async def list_software(
    _current_user: AuthUser = Depends(get_current_user),
):
    """List available software products that can be detected."""
    return [
        SoftwareProductResponse(
            slug=slug,
            name=entry["name"],
            website=entry.get("website"),
        )
        for slug, entry in BUILTIN_PATTERNS.items()
    ]


# ---------------------------------------------------------------------------
# Searches
# ---------------------------------------------------------------------------


@router.post(
    "/searches",
    response_model=SearchResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Unknown software slug"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def create_search(
    request: CreateSearchRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Create a new lead search and kick off discovery + detection."""
    svc = _get_service()

    try:
        params = SearchParams(
            center_lat=request.center_lat,
            center_lng=request.center_lng,
            radius_km=request.radius_km,
            business_type=request.business_type,
            cell_size_km=request.cell_size_km,
        )
        search_id = await svc.create_search(
            software_slug=request.software_slug,
            params=params,
            user_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "BAD_REQUEST", "message": str(e)},
        )

    stats = await svc.run_search(
        search_id=search_id,
        concurrency=request.concurrency,
    )

    return SearchResponse(
        searchID=search_id,
        status="completed",
        softwareSlug=request.software_slug,
        softwareName=BUILTIN_PATTERNS.get(request.software_slug, {}).get("name", request.software_slug),
        stats=SearchStatsResponse(
            businessesFound=stats.businesses_found,
            businessesWithWebsite=stats.businesses_with_website,
            detectedCount=stats.detected_count,
            notDetectedCount=stats.not_detected_count,
            detectionErrors=stats.detection_errors,
            apiCalls=stats.api_calls,
        ),
    )


@router.get(
    "/searches/{search_id}",
    response_model=SearchResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def get_search(
    search_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Get a search by ID (must belong to the current user)."""
    svc = _get_service()
    search = await svc.get_search(search_id, user_id=current_user.user_id)

    if not search:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Search not found"},
        )

    raw_stats = search.get("stats") or {}
    return SearchResponse(
        searchID=search_id,
        status=search["status"],
        softwareSlug=search["software_slug"],
        softwareName=search["software_name"],
        stats=SearchStatsResponse(
            businessesFound=raw_stats.get("businesses_found", 0),
            businessesWithWebsite=raw_stats.get("businesses_with_website", 0),
            detectedCount=raw_stats.get("detected_count", 0),
            notDetectedCount=raw_stats.get("not_detected_count", 0),
            detectionErrors=raw_stats.get("detection_errors", 0),
            apiCalls=raw_stats.get("api_calls", 0),
        ),
        createdAt=str(search.get("created_at", "")),
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@router.get(
    "/searches/{search_id}/results",
    response_model=SearchResultsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def get_search_results(
    search_id: int,
    detected_only: bool = False,
    current_user: AuthUser = Depends(get_current_user),
):
    """Get leads for a search. Use ?detected_only=true to filter."""
    svc = _get_service()
    rows = await svc.get_search_results(
        search_id, user_id=current_user.user_id, detected_only=detected_only
    )

    if rows is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Search not found"},
        )

    leads = [
        LeadResponse(
            leadID=r["id"],
            name=r.get("name", ""),
            website=r.get("website"),
            phone=r.get("phone"),
            email=r.get("email"),
            address=r.get("address"),
            city=r.get("city"),
            state=r.get("state"),
            detectionStatus=r.get("detection_status", "pending"),
            detectedSoftware=r.get("detected_software"),
            detectionMethod=r.get("detection_method"),
            detectionDetails=r.get("detection_details"),
        )
        for r in rows
    ]

    return SearchResultsResponse(
        searchID=search_id,
        leads=leads,
        total=len(leads),
    )
