#!/usr/bin/env python3
"""
LinkedIn Outreach Workflow

This workflow demonstrates how to use the LinkedIn outreach functionality
to connect with multiple profiles at once.
"""

import asyncio

from loguru import logger

from air1.services.outreach.service import Service
from air1.services.outreach.templates import DEFAULT_COLD_CONNECTION_NOTE


async def linkedin_outreach_workflow():
    profile_usernames = ["alexhaffner"]

    async with Service() as service:
        results = await service.connect_with_linkedin_profiles(
            profile_usernames=profile_usernames,
            message=DEFAULT_COLD_CONNECTION_NOTE,
            delay_between_connections=5,
            headless=False,
        )

        logger.info("\n--- LinkedIn Outreach Results ---")
        for username, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"{username}: {status}")

        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"\nSummary: {successful}/{total} connections sent successfully")

        return results


def run():
    asyncio.run(linkedin_outreach_workflow())


if __name__ == "__main__":
    run()
