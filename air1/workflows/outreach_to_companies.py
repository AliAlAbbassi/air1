"""
Outreach to Companies Workflow

Connects with employees at companies from the database and tracks progress.
"""

import asyncio
import random
import time

from loguru import logger

from air1.services.outreach.contact_point import (
    has_linkedin_connection,
    insert_linkedin_connection,
)
from air1.services.outreach.linkedin_locations import DUBAI_EMIRATE
from air1.services.outreach.repo import (
    get_companies_with_outreach_status,
    get_linkedin_profile_by_username,
    increment_company_employees_contacted,
    update_company_outreach,
)
from air1.services.outreach.service import Service


async def outreach_to_company(
    company_name: str,
    company_id: int,
    keywords: list[str] | None = None,
    regions: list[str] | None = None,
    pages: int = 1,
    delay_range: tuple[float, float] = (2.0, 5.0),
) -> int:
    """
    Connect with employees at a specific company and update outreach status.

    Args:
        company_name: Company name (used for search)
        company_id: Company ID in database
        keywords: Keywords to filter employees (e.g., ['recruiter', 'talent'])
        regions: LinkedIn geo region IDs to filter by
        pages: Number of search result pages
        delay_range: Min/max seconds between requests

    Returns:
        Number of successful connections
    """
    async with Service() as service:
        # Update status to in_progress
        await update_company_outreach(company_id=company_id, status="in_progress")

        logger.info(f"Searching for employees at {company_name}...")

        # Search for employees
        # Try to find company by name (linkedin username might not match)
        employees = service.api.search_company_employees(
            company=company_name.lower().replace(" ", "-"),  # Try URL-friendly version
            keywords=keywords,
            regions=regions,
            pages=pages,
        )

        if not employees:
            # Try with original name
            employees = service.api.search_company_employees(
                company=company_name,
                keywords=keywords,
                regions=regions,
                pages=pages,
            )

        logger.info(f"Found {len(employees)} employees at {company_name}")

        if not employees:
            await update_company_outreach(company_id=company_id, status="skipped")
            return 0

        success_count = 0
        skipped_count = 0
        for i, employee in enumerate(employees):
            if not employee.public_id:
                continue

            username = employee.public_id

            # Check if we've already sent a connection request
            already_connected = await has_linkedin_connection(username)
            if already_connected:
                logger.info(f"[{i + 1}/{len(employees)}] Skipping {username} - already connected")
                skipped_count += 1
                continue

            logger.info(f"[{i + 1}/{len(employees)}] Connecting with {username}")

            success = service.send_connection_request(username)

            if success:
                success_count += 1
                await increment_company_employees_contacted(company_id)

                # Track the connection
                try:
                    linkedin_profile = await get_linkedin_profile_by_username(username)
                    lead_id = linkedin_profile.leadId if linkedin_profile else None

                    if not lead_id:
                        lead_id = await service.save_lead_from_api(
                            profile_username=username,
                            company_username=company_name.lower().replace(" ", "-"),
                            job_title=employee.headline,
                        )

                    if lead_id:
                        await insert_linkedin_connection(lead_id)
                        logger.info(f"Tracked connection for {username}")
                except Exception as e:
                    logger.error(f"Failed to track connection for {username}: {e}")

            # Delay between requests
            if i < len(employees) - 1:
                delay = random.uniform(*delay_range)
                time.sleep(delay)

        # Update final status
        status = "completed" if success_count > 0 else "skipped"
        await update_company_outreach(company_id=company_id, status=status)

        logger.success(
            f"Completed {company_name}: {success_count} new, {skipped_count} skipped"
        )
        return success_count


async def outreach_to_pending_companies(
    keywords: list[str] | None = None,
    regions: list[str] | None = None,
    limit: int = 5,
    pages_per_company: int = 1,
    delay_between_companies: float = 10.0,
) -> dict[str, int]:
    """
    Run outreach on all pending companies.

    Args:
        keywords: Keywords to filter employees
        regions: LinkedIn geo region IDs
        limit: Max companies to process
        pages_per_company: Pages of employees to fetch per company
        delay_between_companies: Seconds to wait between companies

    Returns:
        Dict mapping company name to connections made
    """
    # Get pending companies
    companies = await get_companies_with_outreach_status(source="job_search")
    pending = [c for c in companies if c["status"] in ("pending", "not_started")]

    if not pending:
        logger.info("No pending companies to process")
        return {}

    logger.info(f"Found {len(pending)} pending companies, processing {min(limit, len(pending))}")

    results = {}
    for i, company in enumerate(pending[:limit]):
        company_name = company["name"]
        company_id = company["companyId"]

        logger.info(f"\n[{i + 1}/{min(limit, len(pending))}] Processing: {company_name}")

        connections = await outreach_to_company(
            company_name=company_name,
            company_id=company_id,
            keywords=keywords,
            regions=regions,
            pages=pages_per_company,
        )

        results[company_name] = connections

        # Delay between companies
        if i < min(limit, len(pending)) - 1:
            logger.debug(f"Waiting {delay_between_companies}s before next company...")
            time.sleep(delay_between_companies)

    # Summary
    total = sum(results.values())
    logger.success(f"\nOutreach complete: {total} connections across {len(results)} companies")

    return results


async def list_companies(source: str | None = "job_search") -> None:
    """List all companies with their outreach status."""
    companies = await get_companies_with_outreach_status(source=source)

    if not companies:
        logger.info("No companies found")
        return

    print(f"\n{'Company':<40} {'Status':<15} {'Contacted':<10}")
    print("-" * 65)

    for c in companies:
        name = c["name"][:38] if len(c["name"]) > 38 else c["name"]
        print(f"{name:<40} {c['status']:<15} {c['employeesContacted']:<10}")


async def main():
    """Main entry point - list companies and run outreach."""
    # List current status
    await list_companies()

    # Run outreach on pending companies
    await outreach_to_pending_companies(
        keywords=["recruiter", "talent", "hr"],
        regions=[DUBAI_EMIRATE],
        limit=25,  # Process 10 companies
        pages_per_company=1,
    )


if __name__ == "__main__":
    asyncio.run(main())

