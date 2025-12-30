import asyncio
import random
import time

from loguru import logger

from air1.services.outreach.contact_point import insert_linkedin_connection
from air1.services.outreach.linkedin_locations import DUBAI_EMIRATE
from air1.services.outreach.repo import get_linkedin_profile_by_username
from air1.services.outreach.service import Service


async def connect_with_company_members(
    company_username: str,
    keywords: list[str] | None = None,
    regions: list[str] | None = None,
    pages: int = 1,
    delay_range: tuple[float, float] = (2.0, 5.0),
    headless: bool = False,
):
    """
    Search for employees at a company and send connection requests.

    Args:
        company_username: LinkedIn company username (e.g., 'revolut')
        keywords: Keywords to filter employees (e.g., ['recruiter', 'talent'])
        regions: LinkedIn geo region IDs to filter by
        pages: Number of search result pages to process
        delay_range: Min/max seconds to wait between requests (to avoid rate limiting)
        headless: Run browser in headless mode when scraping profiles
    """
    async with Service() as service:
        logger.info(f"Searching for employees at {company_username}...")

        employees = service.api.search_company_employees(
            company=company_username,
            keywords=keywords,
            regions=regions,
            pages=pages,
        )

        logger.info(f"Found {len(employees)} employees matching criteria")

        success_count = 0
        for i, employee in enumerate(employees):
            if not employee.public_id:
                logger.warning(
                    f"[{i + 1}/{len(employees)}] Skipping employee without public_id"
                )
                continue

            username = employee.public_id
            logger.info(f"[{i + 1}/{len(employees)}] Sending request to {username}")

            success = service.send_connection_request(username)

            if success:
                success_count += 1

                # Track the connection
                try:
                    linkedin_profile = await get_linkedin_profile_by_username(username)
                    lead_id = linkedin_profile.leadId if linkedin_profile else None

                    if not lead_id:
                        logger.info(
                            f"Lead not found for {username}, creating from LinkedIn profile"
                        )
                        lead_id = await service.save_lead_from_linkedin_profile(
                            profile_username=username,
                            headless=headless,
                        )

                    if lead_id:
                        await insert_linkedin_connection(lead_id)
                        logger.info(
                            f"Tracked connection for {username} (lead_id={lead_id})"
                        )
                    else:
                        logger.warning(f"Could not create lead for {username}")
                except Exception as e:
                    logger.error(f"Failed to track connection for {username}: {e}")

            # Add random delay between requests to avoid rate limiting
            if i < len(employees) - 1:
                delay = random.uniform(*delay_range)
                logger.debug(f"Waiting {delay:.1f}s before next request...")
                time.sleep(delay)

        logger.success(
            f"Completed: {success_count}/{len(employees)} connection requests sent"
        )
        return success_count


if __name__ == "__main__":
    asyncio.run(
        connect_with_company_members(
            company_username="revolut",
            keywords=["recruiter", "talent"],
            regions=[DUBAI_EMIRATE],
            pages=1,
        )
    )
