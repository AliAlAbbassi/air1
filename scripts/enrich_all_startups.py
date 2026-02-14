"""Enrich all Form D tech/software startups with website, LinkedIn, and Twitter.

Uses Serper.dev Google Search - one query per company returns all 3 URLs.
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

    result = await enrich_websites_flow(
        batch_size=50,
        iterations=0,  # Process all remaining
        concurrency=5,
    )

    elapsed = time.time() - start
    print(f"\n=== DONE ===")
    print(f"Total enriched: {result['total_enriched']}")
    print(f"Elapsed: {elapsed/60:.1f} minutes")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
