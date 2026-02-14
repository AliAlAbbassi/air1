"""Prefect flows for company enrichment with websites and social URLs."""

from prefect import flow, task
from loguru import logger

from air1.config import settings
from air1.services.enrichment.service import Service


@task
async def enrich_websites_task(batch_size: int = 100, concurrency: int = 5) -> int:
    """Task to enrich companies with website data."""
    svc = Service(serper_api_key=settings.serper_api_key)
    return await svc.enrich_websites(batch_size=batch_size, concurrency=concurrency)


@flow(name="enrich-company-websites")
async def enrich_websites_flow(
    batch_size: int = 100, iterations: int = 1, concurrency: int = 5
) -> dict:
    """Flow to enrich Form D startup companies with website data from Serper Google Search.

    Args:
        batch_size: Number of companies per batch
        iterations: Number of batches to process (0 = all remaining)
        concurrency: Number of concurrent API requests (default 5 to avoid rate limits)

    Returns:
        Dict with total_enriched count
    """
    total_enriched = 0

    if iterations == 0:
        iteration = 0
        while True:
            logger.info(f"Starting enrichment batch {iteration + 1}...")
            count = await enrich_websites_task(
                batch_size=batch_size, concurrency=concurrency
            )
            total_enriched += count

            if count == 0:
                logger.info("All companies enriched")
                break

            logger.info(
                f"Batch {iteration + 1} done: {count} enriched (total so far: {total_enriched})"
            )
            iteration += 1
    else:
        for i in range(iterations):
            logger.info(f"Starting enrichment batch {i + 1}/{iterations}...")
            count = await enrich_websites_task(
                batch_size=batch_size, concurrency=concurrency
            )
            total_enriched += count

            if count == 0:
                logger.info("No more companies to enrich")
                break

            logger.info(
                f"Batch {i + 1} done: {count} enriched (total so far: {total_enriched})"
            )

    return {"total_enriched": total_enriched}
