import asyncio

from loguru import logger

from air1.db.prisma_client import disconnect_db
from air1.services.outreach.service import Service


async def company_leads(
    companies: list[str],
    keywords: list[str],
    limit: int = 10,
    headless: bool = True,
    use_proxy: bool = False,
    use_auth: bool = True,
):
    """
    Scrape LinkedIn company leads

    Args:
        companies: List of LinkedIn company IDs
        keywords: Keywords to filter members by headline
        limit: Maximum number of profiles to process per company
        headless: Run browser in headless mode
        use_proxy: Enable proxy rotation (requires PROXY_SERVER env var)
        use_auth: Use LinkedIn authentication (requires LINKEDIN_SID env var)
    """
    logger.info(
        f"Starting company leads scraping for {len(companies)} companies with limit {limit}"
    )
    if use_proxy:
        logger.info("Proxy rotation enabled")
    if not use_auth:
        logger.info("Running in unauthenticated mode - only public data will be scraped")

    try:
        async with Service(use_auth=use_auth) as service:
            results = await service.scrape_company_leads(
                companies, limit=limit, keywords=keywords, headless=headless, use_proxy=use_proxy
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
    """
    Example usage of company leads scraping

    To use with proxy and no authentication (public data only):
        asyncio.run(company_leads(
            companies, keywords, limit=50, headless=False,
            use_proxy=True, use_auth=False
        ))

    Make sure to set these environment variables when using proxies:
        PROXY_SERVER=http://proxy.example.com:8080
        PROXY_USERNAME=your_username  # Optional
        PROXY_PASSWORD=your_password  # Optional
    """
    companies = ["nooncom"]
    keywords = ["talent"]

    # Default: uses authentication, no proxy
    asyncio.run(company_leads(companies, keywords, limit=50, headless=False))

    # Uncomment below to use proxy rotation without authentication:
    # asyncio.run(company_leads(
    #     companies, keywords, limit=50, headless=False,
    #     use_proxy=True, use_auth=False
    # ))


if __name__ == "__main__":
    run()
