"""Pydantic models for LeadGen API."""

from typing import Optional

from pydantic import BaseModel, Field


class CreateSearchRequest(BaseModel):
    """POST /api/leadgen/searches request body."""

    software_slug: str = Field(..., alias="softwareSlug")
    center_lat: float = Field(..., alias="centerLat")
    center_lng: float = Field(..., alias="centerLng")
    radius_km: float = Field(25.0, alias="radiusKm")
    business_type: str = Field("business", alias="businessType")
    cell_size_km: float = Field(2.0, alias="cellSizeKm")
    concurrency: int = 5

    model_config = {"populate_by_name": True}


class SearchResponse(BaseModel):
    """Response for a single search."""

    search_id: int = Field(..., alias="searchID")
    status: str
    software_slug: str = Field(..., alias="softwareSlug")
    software_name: str = Field(..., alias="softwareName")
    stats: "SearchStatsResponse"
    created_at: Optional[str] = Field(None, alias="createdAt")

    model_config = {"populate_by_name": True, "by_alias": True}


class SearchStatsResponse(BaseModel):
    """Stats for a search run."""

    businesses_found: int = Field(0, alias="businessesFound")
    businesses_with_website: int = Field(0, alias="businessesWithWebsite")
    detected_count: int = Field(0, alias="detectedCount")
    not_detected_count: int = Field(0, alias="notDetectedCount")
    detection_errors: int = Field(0, alias="detectionErrors")
    api_calls: int = Field(0, alias="apiCalls")

    model_config = {"populate_by_name": True, "by_alias": True}


class LeadResponse(BaseModel):
    """Response for a single lead."""

    lead_id: int = Field(..., alias="leadID")
    name: str
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    detection_status: str = Field(..., alias="detectionStatus")
    detected_software: Optional[str] = Field(None, alias="detectedSoftware")
    detection_method: Optional[str] = Field(None, alias="detectionMethod")
    detection_details: Optional[dict] = Field(None, alias="detectionDetails")

    model_config = {"populate_by_name": True, "by_alias": True}


class SearchResultsResponse(BaseModel):
    """GET /api/leadgen/searches/{id}/results response."""

    search_id: int = Field(..., alias="searchID")
    leads: list[LeadResponse]
    total: int

    model_config = {"populate_by_name": True, "by_alias": True}


class SoftwareProductResponse(BaseModel):
    """Response for a software product."""

    slug: str
    name: str
    website: Optional[str] = None

    model_config = {"populate_by_name": True, "by_alias": True}


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
