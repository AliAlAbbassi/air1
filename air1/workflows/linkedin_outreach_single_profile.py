#!/usr/bin/env python3
"""
LinkedIn Outreach Single Profile Workflow

This workflow connects with LinkedIn profiles by manually specified profile IDs
and tracks successful connections by inserting contact points.
"""

import asyncio

from loguru import logger

from air1.services.outreach.contact_point import insert_linkedin_connection
from air1.services.outreach.repo import get_linkedin_profile_by_username
from air1.services.outreach.service import Service
from air1.services.outreach.templates import DEFAULT_COLD_CONNECTION_NOTE


async def linkedin_outreach_single_profile_workflow(
    profile_usernames: list[str],
    message: str | None = DEFAULT_COLD_CONNECTION_NOTE,
    delay_between_connections: int = 5,
    headless: bool = False,
) -> dict[str, bool]:
    """
    Connect with LinkedIn profiles by their usernames and track successful connections.

    Args:
        profile_usernames: List of LinkedIn profile usernames (e.g., ['john-doe-123', 'jane-smith'])
        message: Optional connection message to send with each request
        delay_between_connections: Delay in seconds between connections to avoid rate limits
        headless: Run browser in headless mode

    Returns:
        dict: Results for each username mapping to success status
    """
    logger.info(f"Starting LinkedIn outreach for {len(profile_usernames)} profile(s)")

    async with Service() as service:
        results = await service.connect_with_linkedin_profiles(
            profile_usernames=profile_usernames,
            message=message,
            delay_between_connections=delay_between_connections,
            headless=headless,
        )

        # Track successful connections
        for username, success in results.items():
            if success:
                try:
                    linkedin_profile = await get_linkedin_profile_by_username(username)
                    if linkedin_profile and linkedin_profile.leadId:
                        await insert_linkedin_connection(linkedin_profile.leadId)
                        logger.info(
                            f"Tracked connection for {username} (lead_id={linkedin_profile.leadId})"
                        )
                    else:
                        # Lead not found, create from LinkedIn profile
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
                                f"Created and tracked connection for {username} (lead_id={lead_id})"
                            )
                        else:
                            logger.warning(
                                f"Could not create lead for {username}"
                            )
                except Exception as e:
                    logger.error(f"Failed to track connection for {username}: {e}")

        logger.info(f"Connection results: {results}")
        return results


def run():
    # Manual input - specify profile usernames here
    profile_usernames = ["jamesskelt"]

    asyncio.run(
        linkedin_outreach_single_profile_workflow(
            profile_usernames=profile_usernames,
        )
    )


if __name__ == "__main__":
    run()
