"""Serper Maps discovery source with adaptive grid scraping.

Ported from sadie-gtm's GridScraper. Discovers businesses in a geographic
area using the Serper.dev Google Maps API with adaptive grid subdivision.
"""

import math
import asyncio
from typing import Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from air1.services.leadgen.models import DiscoveredBusiness, SearchParams
from air1.services.leadgen.sources.base import DiscoverySource

SERPER_MAPS_URL = "https://google.serper.dev/maps"

# Grid settings
DEFAULT_CELL_SIZE_KM = 2.0
MIN_CELL_SIZE_KM = 0.5
API_RESULT_LIMIT = 20  # Serper returns max 20 results per query

# Zoom levels by cell size
ZOOM_BY_CELL_SIZE = {
    0.5: 15,
    1.0: 15,
    2.0: 14,
    5.0: 13,
    10.0: 12,
}

MAX_CONCURRENT_REQUESTS = 4  # Stay under Serper 5 qps rate limit

# Junk domains to skip
SKIP_DOMAINS = {
    # Social media
    "facebook.com", "instagram.com", "twitter.com", "youtube.com",
    "tiktok.com", "linkedin.com", "yelp.com",
    # Aggregators
    "booking.com", "expedia.com", "hotels.com", "trivago.com",
    "tripadvisor.com", "kayak.com", "priceline.com", "agoda.com",
    "airbnb.com", "vrbo.com",
    # Other junk
    "google.com",
    # Government/education
    ".gov", ".edu", ".mil",
}


class GridCell(BaseModel):
    """A grid cell for geographic searching."""

    lat_min: float
    lat_max: float
    lng_min: float
    lng_max: float
    index: int = 0

    @property
    def center_lat(self) -> float:
        return (self.lat_min + self.lat_max) / 2

    @property
    def center_lng(self) -> float:
        return (self.lng_min + self.lng_max) / 2

    @property
    def size_km(self) -> float:
        height = (self.lat_max - self.lat_min) * 111.0
        width = (self.lng_max - self.lng_min) * 111.0 * math.cos(
            math.radians(self.center_lat)
        )
        return (height + width) / 2

    def subdivide(self) -> list["GridCell"]:
        """Split into 4 smaller cells."""
        mid_lat = self.center_lat
        mid_lng = self.center_lng
        base_idx = self.index * 4
        return [
            GridCell(lat_min=self.lat_min, lat_max=mid_lat, lng_min=self.lng_min, lng_max=mid_lng, index=base_idx),
            GridCell(lat_min=self.lat_min, lat_max=mid_lat, lng_min=mid_lng, lng_max=self.lng_max, index=base_idx + 1),
            GridCell(lat_min=mid_lat, lat_max=self.lat_max, lng_min=self.lng_min, lng_max=mid_lng, index=base_idx + 2),
            GridCell(lat_min=mid_lat, lat_max=self.lat_max, lng_min=mid_lng, lng_max=self.lng_max, index=base_idx + 3),
        ]


class SerperMapsSource(DiscoverySource):
    """Discover businesses via Serper Google Maps API with adaptive grid scraping."""

    def __init__(self, api_key: str, cell_size_km: float = DEFAULT_CELL_SIZE_KM):
        self.api_key = api_key
        self.cell_size_km = cell_size_km
        self._seen_place_ids: set[str] = set()
        self._seen_locations: set[tuple[float, float]] = set()
        self._seen_names: set[str] = set()
        self._api_calls = 0
        self._out_of_credits = False
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    @property
    def api_calls(self) -> int:
        return self._api_calls

    async def discover(self, params: SearchParams) -> list[DiscoveredBusiness]:
        """Discover businesses in a circular region using adaptive grid scraping."""
        lat_deg = params.radius_km / 111.0
        lng_deg = params.radius_km / (
            111.0 * math.cos(math.radians(params.center_lat))
        )

        lat_min = params.center_lat - lat_deg
        lat_max = params.center_lat + lat_deg
        lng_min = params.center_lng - lng_deg
        lng_max = params.center_lng + lng_deg

        # Bounds with 10% buffer for filtering
        lat_buffer = (lat_max - lat_min) * 0.1
        lng_buffer = (lng_max - lng_min) * 0.1
        bounds = (
            lat_min - lat_buffer,
            lat_max + lat_buffer,
            lng_min - lng_buffer,
            lng_max + lng_buffer,
        )

        cells = self._generate_grid(lat_min, lat_max, lng_min, lng_max)
        logger.info(
            f"Starting grid scrape: {len(cells)} cells, "
            f"{self.cell_size_km}km cells, business_type='{params.business_type}'"
        )

        businesses: list[DiscoveredBusiness] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            while cells and not self._out_of_credits:
                # Process 2 cells concurrently
                batch = []
                for _ in range(min(2, len(cells))):
                    if cells:
                        batch.append(cells.pop(0))

                results = await asyncio.gather(
                    *[
                        self._search_cell(client, cell, params.business_type, bounds)
                        for cell in batch
                    ]
                )

                for cell, (cell_businesses, hit_limit) in zip(batch, results):
                    businesses.extend(cell_businesses)

                    # Adaptive subdivision if API limit was hit
                    if hit_limit and cell.size_km > MIN_CELL_SIZE_KM * 2:
                        subcells = cell.subdivide()
                        cells.extend(subcells)
                        logger.debug(
                            f"Subdivided cell at ({cell.center_lat:.3f}, {cell.center_lng:.3f})"
                        )

        logger.info(
            f"Grid scrape done: {len(businesses)} businesses, {self._api_calls} API calls"
        )
        return businesses

    def _generate_grid(
        self,
        lat_min: float,
        lat_max: float,
        lng_min: float,
        lng_max: float,
    ) -> list[GridCell]:
        """Generate grid cells covering the bounding box."""
        center_lat = (lat_min + lat_max) / 2
        height_km = (lat_max - lat_min) * 111.0
        width_km = (lng_max - lng_min) * 111.0 * math.cos(math.radians(center_lat))

        n_lat = max(1, int(math.ceil(height_km / self.cell_size_km)))
        n_lng = max(1, int(math.ceil(width_km / self.cell_size_km)))

        lat_step = (lat_max - lat_min) / n_lat
        lng_step = (lng_max - lng_min) / n_lng

        cells = []
        idx = 0
        for i in range(n_lat):
            for j in range(n_lng):
                cells.append(
                    GridCell(
                        lat_min=lat_min + i * lat_step,
                        lat_max=lat_min + (i + 1) * lat_step,
                        lng_min=lng_min + j * lng_step,
                        lng_max=lng_min + (j + 1) * lng_step,
                        index=idx,
                    )
                )
                idx += 1
        return cells

    async def _search_cell(
        self,
        client: httpx.AsyncClient,
        cell: GridCell,
        business_type: str,
        bounds: tuple[float, float, float, float],
    ) -> tuple[list[DiscoveredBusiness], bool]:
        """Search a single cell with multiple query variations."""
        businesses: list[DiscoveredBusiness] = []
        hit_limit = False

        zoom = self._get_zoom(cell.size_km)

        # Scout query first
        places = await self._search_serper(
            client, business_type, cell.center_lat, cell.center_lng, zoom
        )

        if len(places) >= API_RESULT_LIMIT:
            hit_limit = True

        if not places:
            return businesses, False

        for place in places:
            biz = self._process_place(place, bounds)
            if biz:
                businesses.append(biz)

        # Run 3 more diverse queries for small cells
        if cell.size_km <= 2.5 and places:
            modifiers = ["local", "small", "independent"]
            diverse_queries = [f"{mod} {business_type}" for mod in modifiers]

            results = await asyncio.gather(
                *[
                    self._search_serper(
                        client, q, cell.center_lat, cell.center_lng, zoom
                    )
                    for q in diverse_queries
                ]
            )

            for result_places in results:
                if len(result_places) >= API_RESULT_LIMIT:
                    hit_limit = True
                for place in result_places:
                    biz = self._process_place(place, bounds)
                    if biz:
                        businesses.append(biz)

        return businesses, hit_limit

    async def _search_serper(
        self,
        client: httpx.AsyncClient,
        query: str,
        lat: float,
        lng: float,
        zoom: int,
    ) -> list[dict]:
        """Call Serper Maps API."""
        if self._out_of_credits:
            return []

        async with self._semaphore:
            self._api_calls += 1
            try:
                resp = await client.post(
                    SERPER_MAPS_URL,
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={"q": query, "ll": f"@{lat},{lng},{zoom}z"},
                )

                if resp.status_code == 400 and "credits" in resp.text.lower():
                    logger.warning("Out of Serper credits")
                    self._out_of_credits = True
                    return []

                if resp.status_code != 200:
                    logger.error(f"Serper error {resp.status_code}: {resp.text[:100]}")
                    return []

                return resp.json().get("places", [])
            except Exception as e:
                logger.error(f"Serper request failed: {e}")
                return []

    def _process_place(
        self,
        place: dict,
        bounds: tuple[float, float, float, float],
    ) -> Optional[DiscoveredBusiness]:
        """Process a Serper Maps result into a DiscoveredBusiness."""
        name = place.get("title", "").strip()
        if not name:
            return None

        website = place.get("website", "") or ""
        place_id = place.get("placeId")
        lat = place.get("latitude")
        lng = place.get("longitude")

        # 3-tier dedup: placeId -> location -> name
        if place_id:
            if place_id in self._seen_place_ids:
                return None
            self._seen_place_ids.add(place_id)
        elif lat and lng:
            loc_key = (round(lat, 4), round(lng, 4))
            if loc_key in self._seen_locations:
                return None
            self._seen_locations.add(loc_key)
        else:
            name_lower = name.lower()
            if name_lower in self._seen_names:
                return None
            self._seen_names.add(name_lower)

        # Filter out-of-bounds
        if lat and lng:
            lat_min, lat_max, lng_min, lng_max = bounds
            if not (lat_min <= lat <= lat_max and lng_min <= lng <= lng_max):
                return None

        # Skip junk domains
        if website:
            website_lower = website.lower()
            for domain in SKIP_DOMAINS:
                if domain in website_lower:
                    return None

        # Parse city/state from address
        address = place.get("address", "")
        city, state = self._parse_address(address)

        return DiscoveredBusiness(
            name=name,
            website=place.get("website"),
            phone=place.get("phoneNumber"),
            address=address or None,
            city=city,
            state=state,
            latitude=lat,
            longitude=lng,
            google_place_id=place_id,
            source="serper_maps",
        )

    @staticmethod
    def _get_zoom(cell_size_km: float) -> int:
        for size, zoom in sorted(ZOOM_BY_CELL_SIZE.items()):
            if cell_size_km <= size:
                return zoom
        return 12

    @staticmethod
    def _parse_address(address: str) -> tuple[Optional[str], Optional[str]]:
        """Extract city and state from address string."""
        if not address:
            return None, None
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 2:
            last = parts[-1].split()
            state = last[0] if last and len(last[0]) == 2 else None
            city = parts[-2] if len(parts) >= 2 else None
            return city, state
        return None, None
