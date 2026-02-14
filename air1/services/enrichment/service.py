"""Company enrichment service for adding website, LinkedIn, and Twitter data."""

import asyncio
from abc import ABC, abstractmethod

from loguru import logger

from air1.services.enrichment import repo
from air1.services.enrichment.serper_client import SerperClient


class IService(ABC):
    """Service interface for company enrichment."""

    @abstractmethod
    async def enrich_websites(
        self, batch_size: int = 100, concurrency: int = 5
    ) -> int:
        """Enrich companies with website, LinkedIn, and Twitter URLs."""
        ...


class Service(IService):
    """Enrichment service using Serper.dev Google Search.

    One query per company returns website + LinkedIn + Twitter.
    """

    def __init__(self, serper_api_key: str):
        self.serper = SerperClient(api_key=serper_api_key)

    async def enrich_websites(
        self, batch_size: int = 100, concurrency: int = 5
    ) -> int:
        """Enrich companies with website, LinkedIn, and Twitter from a single search.

        Returns number of companies that got at least one URL.
        """
        companies = await repo.get_companies_without_websites(limit=batch_size)
        if not companies:
            logger.info("No companies without websites remaining")
            return 0

        logger.info(
            f"Enriching {len(companies)} companies ({concurrency} concurrent)..."
        )

        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(company: dict):
            async with sem:
                try:
                    result = await self.serper.search_company(
                        company["name"],
                        city=company.get("city"),
                        state=company.get("state"),
                    )
                    has_data = result["website"] or result["linkedin"] or result["twitter"]
                    if has_data:
                        logger.info(
                            f"✓ {company['name']}: "
                            f"web={result['website'] or '-'} "
                            f"li={result['linkedin'] or '-'} "
                            f"tw={result['twitter'] or '-'}"
                        )
                    return (company["cik"], result)
                except Exception as e:
                    logger.warning(
                        f"Failed to enrich {company['name']} (CIK={company['cik']}): {e}"
                    )
                    return None

        results = await asyncio.gather(*[_fetch_one(c) for c in companies])

        # Collect updates: (cik, website, linkedin, twitter)
        updates = []
        for r in results:
            if r is None:
                continue
            cik, data = r
            if data["website"] or data["linkedin"] or data["twitter"]:
                updates.append((cik, data["website"], data["linkedin"], data["twitter"]))

        if not updates:
            logger.info("No data found for any companies in this batch")
            return 0

        count = await repo.update_companies_enrichment_batch(updates)
        logger.info(f"Enriched {count}/{len(companies)} companies")
        return count
