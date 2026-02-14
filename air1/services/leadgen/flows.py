"""Prefect flows for lead generation and software detection."""

from prefect import flow, task

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.leadgen.models import SearchParams, SearchStats
from air1.services.leadgen.service import Service


@task(log_prints=True)
async def run_search_task(
    search_id: int,
    concurrency: int = 5,
) -> SearchStats:
    """Run detection on a single search."""
    svc = Service(serper_api_key=settings.serper_api_key)
    return await svc.run_search(search_id=search_id, concurrency=concurrency)


@flow(name="leadgen-search", log_prints=True)
async def leadgen_search_flow(
    software_slug: str,
    center_lat: float,
    center_lng: float,
    radius_km: float = 25.0,
    business_type: str = "business",
    cell_size_km: float = 2.0,
    concurrency: int = 5,
    user_id: str | None = None,
) -> dict:
    """Full lead generation pipeline: create search -> discover -> detect.

    Args:
        software_slug: Slug of the software to detect (e.g., 'cloudbeds').
        center_lat: Latitude of search center.
        center_lng: Longitude of search center.
        radius_km: Search radius in km.
        business_type: What to search for on Maps (e.g., 'hotel').
        cell_size_km: Grid cell size in km.
        concurrency: Concurrent detection workers.
        user_id: Optional Clerk user ID.
    """
    try:
        svc = Service(serper_api_key=settings.serper_api_key)

        params = SearchParams(
            center_lat=center_lat,
            center_lng=center_lng,
            radius_km=radius_km,
            business_type=business_type,
            cell_size_km=cell_size_km,
        )

        search_id = await svc.create_search(
            software_slug=software_slug,
            params=params,
            user_id=user_id,
        )

        stats = await run_search_task(
            search_id=search_id,
            concurrency=concurrency,
        )

        return {
            "search_id": search_id,
            "stats": stats.model_dump(),
        }
    finally:
        await disconnect_db()
