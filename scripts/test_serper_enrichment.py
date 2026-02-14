"""Test script for Serper enrichment on Form D startups."""

import asyncio
import time

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.enrichment.flows import enrich_websites_flow

settings.configure_logging()


async def main():
    if not settings.serper_api_key:
        print("ERROR: SERPER_API_KEY not set in environment")
        print("Get your free API key at https://serper.dev/")
        return

    print(f"Serper API key: {settings.serper_api_key[:10]}...")
    print(f"Free quota: 2,500 queries\n")

    start = time.time()

    # Run enrichment for 1 batch of 20 companies (to test)
    result = await enrich_websites_flow(batch_size=20, iterations=1, concurrency=5)

    elapsed = time.time() - start
    print(f"\n=== DONE ===")
    print(f"Total enriched: {result['total_enriched']}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Queries used: ~{20} / 2,500 free")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
