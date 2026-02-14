"""Prefect flows for company enrichment with websites and social URLs."""

from loguru import logger
from prefect import flow, task

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.enrichment.service import Service


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(log_prints=True)
async def enrich_websites_task(batch_size: int = 100, concurrency: int = 5) -> int:
    """Enrich one batch of companies with website, LinkedIn, and Twitter."""
    svc = Service(serper_api_key=settings.serper_api_key)
    return await svc.enrich_websites(batch_size=batch_size, concurrency=concurrency)


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------


@flow(name="enrich-company-websites", log_prints=True)
async def enrich_websites_flow(
    batch_size: int = 50,
    iterations: int = 0,
    concurrency: int = 5,
):
    """Enrich Form D software companies with website, LinkedIn, and Twitter.

    Args:
        batch_size: Number of companies per batch
        iterations: Number of batches (0 = all remaining)
        concurrency: Concurrent Serper API requests
    """
    try:
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
                    f"Batch {iteration + 1} done: {count} enriched "
                    f"(total so far: {total_enriched})"
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
                    f"Batch {i + 1} done: {count} enriched "
                    f"(total so far: {total_enriched})"
                )

        return {"total_enriched": total_enriched}
    finally:
        await disconnect_db()
