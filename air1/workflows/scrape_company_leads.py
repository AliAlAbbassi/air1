import asyncio

from loguru import logger

from air1.db.prisma_client import disconnect_db
from air1.services.outreach.service import Service


async def company_leads(companies: list[str], keywords: list[str], limit: int = 10):
    logger.info(
        f"Starting company leads scraping for {len(companies)} companies with limit {limit}"
    )
    try:
        async with Service() as service:
            results = await service.scrape_company_leads(
                companies, limit=limit, keywords=keywords
            )
            for company, count in results.items():
                logger.info(f"{company}: {count} leads saved")
    except Exception as e:
        logger.error(f"Error during company leads scraping: {e}")
        raise
    finally:
        await disconnect_db()
        logger.info("Finished company leads workflow")


def run():
    companies = ["aavelabs"]
    keywords = ["talent"]
    asyncio.run(company_leads(companies, keywords, limit=10))


run()
