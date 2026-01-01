"""
Scrape Companies from Job Listings Workflow

Searches LinkedIn job postings and saves unique companies to the database.
"""

import asyncio

from loguru import logger

from air1.services.outreach.linkedin_api import LinkedInAPI
from air1.services.outreach.linkedin_locations import DUBAI_EMIRATE
from air1.services.outreach.repo import save_companies_from_jobs
from air1.services.outreach.service import Service


async def scrape_companies_from_jobs(
    geo_id: str,
    keywords: str | None = None,
    pages: int = 1,
) -> list[int]:
    """
    Scrape companies from LinkedIn job listings and save them to the database.

    Args:
        geo_id: LinkedIn geo ID for location filter (e.g., '106204383' for Dubai)
        keywords: Optional job search keywords
        pages: Number of pages to fetch (25 jobs per page)

    Returns:
        List of saved company IDs
    """
    async with Service() as service:
        logger.info(f"Searching jobs: geo_id={geo_id}, keywords={keywords}, pages={pages}")

        # Get companies from job listings
        companies = service.api.get_companies_from_jobs(
            geo_id=geo_id,
            keywords=keywords,
            pages=pages,
        )

        logger.info(f"Found {len(companies)} unique companies")

        # Save to database
        company_ids = await save_companies_from_jobs(companies, geo_id=geo_id)
        logger.success(f"Saved {len(company_ids)} companies to database")

        return company_ids


if __name__ == "__main__":
    asyncio.run(
        scrape_companies_from_jobs(
            geo_id=DUBAI_EMIRATE,
            keywords=None,
            pages=2,
        )
    )
