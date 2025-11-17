from air1.services.browser.service import Service
from typing import Optional
from loguru import logger


async def linkedin_outreach_workflow(
    profile_usernames: list[str],
    message: Optional[str] = None,
    delay_between_connections: int = 5,
    headless: bool = True
) -> dict[str, bool]:
    """
    LinkedIn outreach workflow to connect with multiple profiles

    Args:
        profile_usernames: List of LinkedIn profile usernames
        message: Optional connection message
        delay_between_connections: Delay in seconds between connections
        headless: Run browser in headless mode

    Returns:
        dict: Results for each username (True if successful, False otherwise)
    """
    async with Service() as service:
        results = await service.connect_with_linkedin_profiles(
            profile_usernames=profile_usernames,
            message=message,
            delay_between_connections=delay_between_connections,
            headless=headless
        )

        # Log summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"LinkedIn outreach completed: {successful}/{total} connections sent successfully")

        return results