"""Enrich all Form D tech/software startups with website data using Serper.dev.

This script will enrich the ~986 filtered Form D companies (tech startups that have
actually raised capital, excluding funds and non-tech companies).

Free Serper quota: 2,500 queries
Expected usage: ~986 queries (if all not found)
"""

import asyncio
import time

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.enrichment.flows import enrich_websites_flow

settings.configure_logging()


async def main():
    if not settings.serper_api_key:
        print("\n❌ ERROR: SERPER_API_KEY not set in environment")
        print("1. Sign up for free at https://serper.dev/")
        print("2. Get your API key from the dashboard")
        print("3. Set it in your .env file: SERPER_API_KEY=your-key-here\n")
        return

    print(f"\n🔑 Serper API key configured")
    print(f"📊 Free quota: 2,500 queries")
    print(f"🎯 Target: ~986 Form D tech/software startups\n")

    start = time.time()

    # Run enrichment for all companies (iterations=0 means process all)
    # Using batch_size=50 and concurrency=5 to be gentle on the API
    result = await enrich_websites_flow(
        batch_size=50,
        iterations=0,  # Process all remaining
        concurrency=5,  # 5 concurrent requests
    )

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"✅ ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"Total enriched: {result['total_enriched']}")
    print(f"Elapsed: {elapsed/60:.1f} minutes")
    print(f"Avg: {elapsed/result['total_enriched']:.1f}s per company" if result['total_enriched'] > 0 else "")
    print(f"Queries used: ~{result['total_enriched']} / 2,500 free\n")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
