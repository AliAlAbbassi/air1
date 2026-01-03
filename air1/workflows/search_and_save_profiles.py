"""
Search and Save Profiles Workflow

Searches LinkedIn for people matching criteria and saves them as leads for later outreach.
"""

import asyncio

from loguru import logger

from air1.services.outreach.linkedin_locations import DUBAI_EMIRATE
from air1.services.outreach.service import Service


async def search_and_save_profiles(
    keywords: str,
    regions: list[str] | None = None,
    pages: int = 1,
) -> list[int]:
    """
    Search LinkedIn for people and save them as leads.

    Args:
        keywords: Search keywords (e.g., "technical recruiter")
        regions: LinkedIn geo region IDs to filter by
        pages: Number of pages to fetch (10 results per page)

    Returns:
        List of lead IDs that were saved
    """
    async with Service() as service:
        logger.info(f"Searching for '{keywords}' - pages={pages}, regions={regions}")

        # Search for people
        profiles = service.api.search_people(
            keywords=keywords,
            regions=regions,
            pages=pages,
        )

        logger.info(f"Found {len(profiles)} profiles")

        saved_lead_ids = []
        skipped_count = 0

        for i, profile in enumerate(profiles):
            if not profile.public_id:
                continue

            username = profile.public_id

            # Check if already exists using service method
            exists = await service.profile_exists(username)
            if exists:
                logger.debug(f"[{i + 1}/{len(profiles)}] Skipping {username} - already exists")
                skipped_count += 1
                continue

            # Save the profile as a lead
            logger.info(f"[{i + 1}/{len(profiles)}] Saving {username}")

            lead_id = await service.save_lead_from_api(
                profile_username=username,
                job_title=profile.headline,
            )

            if lead_id:
                saved_lead_ids.append(lead_id)
                logger.success(f"Saved {profile.name} (ID: {lead_id})")
            else:
                logger.warning(f"Could not save {username}")

        logger.success(
            f"Complete: {len(saved_lead_ids)} saved, {skipped_count} skipped (already exist)"
        )
        return saved_lead_ids


async def list_saved_profiles(limit: int = 50) -> None:
    """List recently saved profiles with their connection status."""
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


if __name__ == "__main__":
    # Search and save profiles
    asyncio.run(
        search_and_save_profiles(
            keywords="technical recruiter",
            regions=[DUBAI_EMIRATE],
            pages=2,  # 20 results
        )
    )

    # List saved profiles
    # asyncio.run(list_saved_profiles())
