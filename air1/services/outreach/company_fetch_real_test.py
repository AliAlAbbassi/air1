import os

import pytest
from loguru import logger

from air1.services.outreach.service import Service


@pytest.mark.asyncio
@pytest.mark.online
async def test_fetch_company_real_browser():
    """
    Test scraping a real company from LinkedIn using a live browser session.

    Usage:
        LINKEDIN_SID="your_cookie" uv run pytest air1/services/outreach/company_fetch_real_test.py --online
    """
    # Ensure LINKEDIN_SID is present
    if not os.getenv("LINKEDIN_SID"):
        pytest.skip("LINKEDIN_SID environment variable not set - skipping online test")

    # Target company to test
    target_url = "https://www.linkedin.com/company/google"

    logger.info(f"Testing with URL: {target_url}")

    async with Service() as service:
        try:
            result = await service.fetch_company_from_linkedin(target_url)

            logger.info(f"Successfully fetched company: {result.name}")
            logger.info(f"Description: {result.description[:100]}...")
            logger.info(f"Website: {result.website}")
            logger.info(f"Industry: {result.industry}")

            assert result.name is not None
            assert len(result.name) > 0
            # Google should definitely have a website
            assert result.website is not None

        except Exception as e:
            pytest.fail(f"Failed to fetch company: {e}")
