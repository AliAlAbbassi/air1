import asyncio

from loguru import logger

from air1.db.prisma_client import disconnect_db
from air1.services.outreach.service import Service


async def company_leads(
    companies: list[str],
    keywords: list[str],
    limit: int = 10,
    location_ids: list[str] | None = None,
):
    logger.info(
        f"Starting company leads scraping for {len(companies)} companies with limit {limit}"
    )
    try:
        async with Service() as service:
            results = await service.scrape_company_leads(
                companies, limit=limit, keywords=keywords, location_ids=location_ids
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
    companies = ["murex"]
    keywords = ["talent"]
    location_ids = ["105606446", "101834488"]  # LinkedIn geo region IDs
    asyncio.run(company_leads(companies, keywords, limit=10, location_ids=location_ids))


run()
