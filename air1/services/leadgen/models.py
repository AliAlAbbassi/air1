"""Pydantic models for the leadgen service."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class SoftwareProduct(BaseModel):
    """A software product that can be detected on websites."""

    model_config = ConfigDict(from_attributes=True)

    id: int = 0
    name: str
    slug: str
    website: Optional[str] = None
    detection_patterns: dict = {}


class SearchParams(BaseModel):
    """Parameters for a lead search."""

    center_lat: float
    center_lng: float
    radius_km: float = 25.0
    business_type: str = "business"
    cell_size_km: float = 2.0


class DiscoveredBusiness(BaseModel):
    """A business discovered from a source (before detection)."""

    name: str
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    source: str = "serper_maps"


class DetectionResult(BaseModel):
    """Result of software detection on a single website."""

    detected: bool = False
    software_name: str = ""
    method: str = ""  # html_pattern, url_match, network_sniff
    confidence: float = 0.0
    booking_url: str = ""
    error: str = ""


class SearchStats(BaseModel):
    """Statistics for a completed search run."""

    businesses_found: int = 0
    businesses_with_website: int = 0
    detected_count: int = 0
    not_detected_count: int = 0
    detection_errors: int = 0
    api_calls: int = 0
    cells_searched: int = 0
