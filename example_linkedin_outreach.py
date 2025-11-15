#!/usr/bin/env python3
"""
Example usage of the LinkedIn Outreach workflow

This example demonstrates how to use the new LinkedIn outreach functionality
to connect with multiple profiles at once.
"""

import asyncio
from air1.services.browser.service import Service


async def main():
    # List of LinkedIn profile usernames to connect with
    profile_usernames = [
        "john-doe-123",
        "jane-smith-456",
        "bob-wilson-789",
        "alice-johnson-321"
    ]

    # Optional custom message for connection requests
    custom_message = """Hi! I came across your profile and was impressed by your experience.
I'd love to connect and learn more about your work in the industry."""

    # Initialize the service (requires LINKEDIN_SID environment variable)
    async with Service() as service:
        # Connect with all profiles
        results = await service.connect_with_linkedin_profiles(
            profile_usernames=profile_usernames,
            message=custom_message,  # Optional - can be None for no message
            delay_between_connections=5,  # Wait 5 seconds between connections
            headless=True  # Run in headless mode (set to False to see browser)
        )

        # Print results
        print("\n--- LinkedIn Outreach Results ---")
        for username, success in results.items():
            status = "✓ SUCCESS" if success else "✗ FAILED"
            print(f"{username}: {status}")

        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        print(f"\nSummary: {successful}/{total} connections sent successfully")


if __name__ == "__main__":
    asyncio.run(main())