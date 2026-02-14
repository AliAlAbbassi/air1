"""Test script for Brandfetch enrichment."""

import asyncio
import time

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.enrichment.flows import enrich_websites_flow

settings.configure_logging()


async def main():
    start = time.time()

    # Run enrichment for 1 batch of 50 companies
    result = await enrich_websites_flow(batch_size=50, iterations=1, concurrency=10)

    elapsed = time.time() - start
    print(f"\n=== DONE ===")
    print(f"Total enriched: {result['total_enriched']}")
    print(f"Elapsed: {elapsed:.1f}s")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
