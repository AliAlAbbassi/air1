#!/usr/bin/env python3
"""
LinkedIn Outreach Workflow

This workflow demonstrates how to use the LinkedIn outreach functionality
to connect with multiple profiles at once.
"""

import asyncio
from air1.services.browser.service import Service
from loguru import logger


async def linkedin_outreach_workflow():
    profile_usernames = [
        "john-doe-123",
        "jane-smith-456",
        "bob-wilson-789",
        "alice-johnson-321",
    ]

    custom_message = """Hi! I came across your profile and was impressed by your experience.
I'd love to connect and learn more about your work in the industry."""

    async with Service() as service:
        results = await service.connect_with_linkedin_profiles(
            profile_usernames=profile_usernames,
            message=custom_message,
            delay_between_connections=5,
            headless=True,
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
