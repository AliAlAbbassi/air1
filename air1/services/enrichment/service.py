"""Company enrichment service for adding website, logo, and LinkedIn data."""

import asyncio
from loguru import logger

from air1.services.enrichment import repo
from air1.services.enrichment.serper_client import SerperClient


class EnrichmentService:
    """Service for enriching company data with websites via Serper.dev Google Search.

    Usage:
        svc = EnrichmentService(serper_api_key="your-key")
        count = await svc.enrich_websites(batch_size=100)
    """

    def __init__(self, serper_api_key: str):
        """Initialize enrichment service.

        Args:
            serper_api_key: Serper.dev API key (2,500 free queries)
        """
        self.serper = SerperClient(api_key=serper_api_key)

    async def enrich_websites(
        self, batch_size: int = 100, concurrency: int = 5
    ) -> int:
        """Enrich Form D startup companies with website data from Serper Google Search.

        Args:
            batch_size: Number of companies to process
            concurrency: Number of concurrent API requests (default 5 to avoid rate limits)

        Returns:
            Number of companies successfully enriched
        """
        companies = await repo.get_companies_without_websites(limit=batch_size)
        if not companies:
            logger.info("No companies without websites remaining")
            return 0

        logger.info(
            f"Enriching {len(companies)} companies with websites ({concurrency} concurrent)..."
        )

        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(company: dict):
            async with sem:
                try:
                    website = await self.serper.search_company(
                        company["name"],
                        city=company.get("city"),
                        state=company.get("state"),
                    )
                    if website:
                        logger.info(f"✓ Found {company['name']}: {website}")
                        return (company["cik"], website)
                    else:
                        logger.debug(f"✗ Not found: {company['name']}")
                        return None
                except Exception as e:
                    logger.warning(
                        f"Failed to enrich {company['name']} (CIK={company['cik']}): {e}"
                    )
                    return None

        results = await asyncio.gather(*[_fetch_one(c) for c in companies])
        updates = [r for r in results if r is not None]

        if not updates:
            logger.info("No website data found for any companies in this batch")
            return 0

        # Batch update to DB
        count = await repo.update_companies_websites_batch(updates)
        logger.info(f"Enriched {count}/{len(companies)} companies with websites")
        return count
