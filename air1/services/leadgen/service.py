"""LeadGen service — orchestrates business discovery and software detection."""

import json
from abc import ABC, abstractmethod

from loguru import logger

from air1.services.leadgen import repo
from air1.services.leadgen.detector import SoftwareDetector
from air1.services.leadgen.models import (
    SearchParams,
    SearchStats,
)
from air1.services.leadgen.patterns import BUILTIN_PATTERNS
from air1.services.leadgen.sources.serper_maps import SerperMapsSource


class IService(ABC):
    """Interface for the leadgen service."""

    @abstractmethod
    async def create_search(
        self,
        software_slug: str,
        params: SearchParams,
        user_id: str | None = None,
    ) -> int: ...

    @abstractmethod
    async def run_search(
        self, search_id: int, concurrency: int = 5
    ) -> SearchStats: ...


class Service(IService):
    """LeadGen service — discover businesses and detect their software."""

    def __init__(self, serper_api_key: str):
        self.serper_api_key = serper_api_key

    async def create_search(
        self,
        software_slug: str,
        params: SearchParams,
        user_id: str | None = None,
    ) -> int:
        """Create a lead search, ensuring the software product exists.

        If the slug matches a built-in pattern, upserts it automatically.
        Returns the search ID.
        """
        # Ensure software product exists
        product = await repo.get_software_product(software_slug)
        if not product:
            # Try built-in patterns
            builtin = BUILTIN_PATTERNS.get(software_slug)
            if not builtin:
                raise ValueError(
                    f"Unknown software '{software_slug}'. "
                    f"Available built-ins: {list(BUILTIN_PATTERNS.keys())}"
                )
            product = await repo.upsert_software_product(
                name=builtin["name"],
                slug=software_slug,
                website=builtin.get("website"),
                detection_patterns=builtin["detection_patterns"],
            )

        search_id = await repo.create_lead_search(
            software_product_id=product["id"],
            search_params=params.model_dump(),
            user_id=user_id,
        )
        logger.info(f"Created lead search #{search_id} for {software_slug}")
        return search_id

    async def run_search(
        self, search_id: int, concurrency: int = 5
    ) -> SearchStats:
        """Execute the full pipeline: discover -> detect -> store.

        1. Fetch software product and its detection patterns
        2. Discover businesses via SerperMaps grid scraping
        3. Store discovered businesses
        4. Detect software on each business website
        5. Update results and stats
        """
        search = await repo.get_lead_search(search_id)
        if not search:
            raise ValueError(f"Search #{search_id} not found")

        product = await repo.get_software_product_by_id(search["software_product_id"])
        if not product:
            raise ValueError("Software product not found")

        params_dict = search["search_params"]
        if isinstance(params_dict, str):
            params_dict = json.loads(params_dict)
        params = SearchParams(**params_dict)

        detection_patterns = product["detection_patterns"]
        if isinstance(detection_patterns, str):
            detection_patterns = json.loads(detection_patterns)

        software_name = product["name"]
        stats = SearchStats()

        # Phase 1: Discovery
        logger.info(f"[Search #{search_id}] Phase 1: Discovering businesses...")
        await repo.update_search_status(search_id, "scraping")

        source = SerperMapsSource(
            api_key=self.serper_api_key,
            cell_size_km=params.cell_size_km,
        )
        businesses = await source.discover(params)
        stats.businesses_found = len(businesses)
        stats.api_calls = source.api_calls

        if not businesses:
            logger.info(f"[Search #{search_id}] No businesses found")
            await repo.update_search_status(
                search_id, "completed", stats.model_dump()
            )
            return stats

        # Store discovered businesses
        leads_data = [biz.model_dump() for biz in businesses]
        await repo.batch_insert_leads(search_id, leads_data)

        stats.businesses_with_website = sum(
            1 for b in businesses if b.website
        )
        logger.info(
            f"[Search #{search_id}] Found {stats.businesses_found} businesses "
            f"({stats.businesses_with_website} with websites)"
        )

        # Phase 2: Detection
        logger.info(f"[Search #{search_id}] Phase 2: Detecting {software_name}...")
        await repo.update_search_status(search_id, "detecting")

        pending = await repo.get_pending_leads(search_id)
        if not pending:
            logger.info(f"[Search #{search_id}] No leads with websites to detect")
            await repo.update_search_status(
                search_id, "completed", stats.model_dump()
            )
            return stats

        websites = [(lead["id"], lead["website"]) for lead in pending]

        async with SoftwareDetector() as detector:
            results = await detector.detect_batch(
                websites=websites,
                detection_patterns=detection_patterns,
                software_name=software_name,
                concurrency=concurrency,
            )

        # Store detection results
        for lead_id, result in results.items():
            if result.detected:
                stats.detected_count += 1
                await repo.update_lead_detection(
                    lead_id=lead_id,
                    detection_status="detected",
                    detected_software=result.software_name,
                    detection_method=result.method,
                    detection_details={
                        "booking_url": result.booking_url,
                        "confidence": result.confidence,
                    },
                )
            elif result.error:
                stats.detection_errors += 1
                await repo.update_lead_detection(
                    lead_id=lead_id,
                    detection_status="error",
                    detection_details={"error": result.error},
                )
            else:
                stats.not_detected_count += 1
                await repo.update_lead_detection(
                    lead_id=lead_id,
                    detection_status="not_detected",
                )

        # Complete
        await repo.update_search_status(search_id, "completed", stats.model_dump())
        logger.info(
            f"[Search #{search_id}] Done: {stats.detected_count} detected, "
            f"{stats.not_detected_count} not detected, "
            f"{stats.detection_errors} errors"
        )

        return stats
