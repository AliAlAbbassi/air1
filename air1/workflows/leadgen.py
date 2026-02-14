"""Workflow entry point for lead generation.

Usage:
    uv run python air1/workflows/leadgen.py
"""

import asyncio

from air1.config import settings
from air1.services.leadgen.flows import leadgen_search_flow

settings.configure_logging()


async def main():
    result = await leadgen_search_flow(
        software_slug="cloudbeds",
        center_lat=25.7617,   # Miami
        center_lng=-80.1918,
        radius_km=10,
        business_type="hotel",
        concurrency=5,
    )
    print(f"Search #{result['search_id']} complete")
    print(f"Stats: {result['stats']}")


if __name__ == "__main__":
    asyncio.run(main())
