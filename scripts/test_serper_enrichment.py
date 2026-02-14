"""Test Serper enrichment on a small batch of 5 companies.

Extracts website, LinkedIn, and Twitter from a single search query per company.
"""

import asyncio
import time

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.enrichment.flows import enrich_websites_flow

settings.configure_logging()


async def main():
    if not settings.serper_api_key:
        print("ERROR: SERPER_API_KEY not set in .env")
        return

    start = time.time()

    # Small batch: 5 companies, 1 iteration
    result = await enrich_websites_flow(batch_size=5, iterations=1, concurrency=3)

    elapsed = time.time() - start
    print(f"\n=== DONE ===")
    print(f"Total enriched: {result['total_enriched']}")
    print(f"Elapsed: {elapsed:.1f}s")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
