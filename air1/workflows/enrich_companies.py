"""Company enrichment workflow entrypoint.

Enriches Form D software companies with website, LinkedIn, and Twitter
using Serper.dev Google Search (one query per company).

Usage:
    python air1/workflows/enrich_companies.py
"""

import asyncio
import sys

from loguru import logger

from air1.config import settings
from air1.services.enrichment.flows import enrich_websites_flow

settings.configure_logging()

if __name__ == "__main__":
    if not settings.serper_api_key:
        print("ERROR: SERPER_API_KEY not set in .env")
        sys.exit(1)

    result = asyncio.run(
        enrich_websites_flow(batch_size=50, iterations=0, concurrency=5)
    )
    logger.info(f"Enrichment complete: {result}")
