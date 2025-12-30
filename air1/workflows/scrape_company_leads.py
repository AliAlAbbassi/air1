import asyncio

from loguru import logger

from air1.db.prisma_client import disconnect_db
from air1.services.outreach.service import Service


async def company_leads(
    companies: list[str],
    keywords: list[str],
    limit: int = 10,
    location_ids: list[str] | None = None,
    profile_limit: int | None = None,
    headless: bool = True,
):
    logger.info(
        f"Starting company leads scraping for {len(companies)} companies with limit {limit}"
        + (f", profile_limit {profile_limit}" if profile_limit else "")
    )
    try:
        async with Service() as service:
            results = await service.scrape_company_leads(
                companies,
                limit=limit,
                keywords=keywords,
                location_ids=location_ids,
                profile_limit=profile_limit,
                headless=headless,
            )
            for company, count in results.items():
                logger.info(f"{company}: {count} leads saved")
    except Exception as e:
        logger.error(f"Error during company leads scraping: {e}")
        raise
    finally:
        await disconnect_db()
        logger.info("Finished company leads workflow")


# https://www.linkedin.com/company/murex/people/?facetGeoRegion=105606446%2C101834488&keywords=talent
def run():
    companies = ["yeet"]
    keywords = [
        "talent",
        "recruiter",
        "engineering manager",
        "techlead",
        "lead",
        "talent acquisition",
    ]
    location_ids = []
    # profile_limit limits the number of profiles to process (e.g., 20 out of 124 found)
    asyncio.run(
        company_leads(
            companies,
            keywords,
            limit=20,
            location_ids=location_ids,
            profile_limit=20,
        )
    )


run()
