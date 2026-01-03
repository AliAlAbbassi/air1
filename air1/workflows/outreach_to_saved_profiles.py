"""
Outreach to Saved Profiles Workflow

Sends connection requests to profiles saved in the database.
Skips profiles we've already connected with.
"""

import asyncio
import random
import time

from loguru import logger

from air1.services.outreach.service import Service


async def outreach_to_saved_profiles(
    limit: int = 20,
    delay_range: tuple[float, float] = (2.0, 5.0),
) -> dict[str, bool]:
    """
    Send connection requests to saved profiles.

    Args:
        limit: Maximum number of profiles to contact
        delay_range: Min/max seconds between requests

    Returns:
        Dict mapping username to success status
    """
    async with Service() as service:
        # Get profiles to contact (already filters out connected ones)
        profiles = await service.get_profiles_for_outreach(limit=limit)

        if not profiles:
            logger.info("No profiles to contact (all already connected or no saved profiles)")
            return {}

        logger.info(f"Found {len(profiles)} profiles to contact")

        results = {}

        for i, profile in enumerate(profiles):
            username = profile["username"]
            lead_id = profile["lead_id"]
            name = profile["name"] or username

            logger.info(f"[{i + 1}/{len(profiles)}] Connecting with {name} ({username})")

            # Send connection request
            success = service.send_connection_request(username)

            if success:
                results[username] = True
                logger.success(f"Connection request sent to {name}")

                # Track the connection
                if lead_id:
                    await service.track_connection_request(lead_id)
                    logger.info(f"Tracked connection for {username}")
            else:
                results[username] = False
                logger.error(f"Failed to connect with {name}")

            # Delay between requests
            if i < len(profiles) - 1:
                delay = random.uniform(*delay_range)
                time.sleep(delay)

        # Summary
        success_count = sum(1 for v in results.values() if v)
        logger.success(
            f"Outreach complete: {success_count}/{len(profiles)} connections sent"
        )

        return results


async def list_profiles_status(limit: int = 50) -> None:
    """List saved profiles with their connection status."""
    async with Service() as service:
        profiles = await service.get_all_saved_profiles(limit=limit)

        connected_count = sum(1 for p in profiles if p["is_connected"])
        pending_count = len(profiles) - connected_count

        print(f"\n{'Username':<35} {'Name':<25} {'Status':<12}")
        print("-" * 72)

        for p in profiles:
            name = p["name"][:23] if p["name"] else "N/A"
            status = "Connected" if p["is_connected"] else "Pending"
            print(f"{p['username'][:33]:<35} {name:<25} {status:<12}")

        print("-" * 72)
        print(f"Total: {connected_count} connected, {pending_count} pending outreach")


async def main():
    """Main entry point."""
    async with Service() as service:
        # Show current status
        profiles = await service.get_all_saved_profiles(limit=30)

        connected_count = sum(1 for p in profiles if p["is_connected"])
        pending_count = len(profiles) - connected_count

        print(f"\n{'Username':<35} {'Name':<25} {'Status':<12}")
        print("-" * 72)

        for p in profiles:
            name = p["name"][:23] if p["name"] else "N/A"
            status = "Connected" if p["is_connected"] else "Pending"
            print(f"{p['username'][:33]:<35} {name:<25} {status:<12}")

        print("-" * 72)
        print(f"Total: {connected_count} connected, {pending_count} pending outreach")

    # Run outreach
    await outreach_to_saved_profiles(
        limit=10,  # Contact 10 profiles
        delay_range=(2.0, 4.0),
    )


if __name__ == "__main__":
    asyncio.run(main())
