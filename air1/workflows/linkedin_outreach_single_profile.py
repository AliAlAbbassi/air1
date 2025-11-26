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
    profile_ids: list[str],
    message: str | None = DEFAULT_COLD_CONNECTION_NOTE,
    delay_between_connections: int = 5,
    headless: bool = False,
) -> dict[str, bool]:
    """
    Connect with LinkedIn profiles by their profile IDs and track successful connections.

    Args:
        profile_ids: List of LinkedIn profile IDs/usernames (e.g., ['john-doe-123', 'jane-smith'])
        message: Optional connection message to send with each request
        delay_between_connections: Delay in seconds between connections to avoid rate limits
        headless: Run browser in headless mode

    Returns:
        dict: Results for each profile ID mapping to success status
    """
    logger.info(f"Starting LinkedIn outreach for {len(profile_ids)} profile(s)")

    async with Service() as service:
        results = await service.connect_with_linkedin_profiles(
            profile_usernames=profile_ids,
            message=message,
            delay_between_connections=delay_between_connections,
            headless=headless,
        )

        # Track successful connections
        for profile_id, success in results.items():
            if success:
                linkedin_profile = await get_linkedin_profile_by_username(profile_id)
                if linkedin_profile and linkedin_profile.leadId:
                    await insert_linkedin_connection(linkedin_profile.leadId)
                    logger.info(
                        f"Tracked connection for {profile_id} (lead_id={linkedin_profile.leadId})"
                    )
                else:
                    logger.warning(
                        f"Could not track connection for {profile_id}: profile not found in database"
                    )

        logger.info(f"Connection results: {results}")
        return results


def run():
    # Manual input - specify profile IDs here
    profile_ids = ["profile_id_here", "another_one"]

    asyncio.run(
        linkedin_outreach_single_profile_workflow(
            profile_ids=profile_ids,
        )
    )


if __name__ == "__main__":
    run()
