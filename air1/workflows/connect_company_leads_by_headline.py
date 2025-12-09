#!/usr/bin/env python3
"""
LinkedIn Outreach Workflow

This workflow demonstrates how to use the LinkedIn outreach functionality
to connect with multiple profiles at once.
"""

import asyncio

from air1.services.outreach.service import Service
from air1.services.outreach.templates import DEFAULT_COLD_CONNECTION_NOTE


async def linkedin_outreach_workflow(
    company_username: str = "google",
    headline_search_term: str = "talent",
    limit: int = 10,
    headless: bool = False,
):
    from loguru import logger

    logger.info(
        f"Starting LinkedIn outreach for {company_username} with headline '{headline_search_term}'"
    )

    async with Service() as service:
        leads = await service.get_company_leads_by_headline(
            company_username=company_username,
            search_term=headline_search_term,
            limit=limit,
        )

        if not leads:
            logger.warning(
                f"No leads found for {company_username} with headline '{headline_search_term}'"
            )
            return {}

        logger.info(f"Found {len(leads)} leads")
        username_lead_mapping = {lead.username: lead.lead_id for lead in leads}

        results = await service.connect_with_linkedin_profiles_tracked(
            username_lead_mapping=username_lead_mapping,
            message=DEFAULT_COLD_CONNECTION_NOTE,
            delay_between_connections=5,
            headless=headless,
        )

        logger.info(f"Connection results: {results}")
        return results


def run():
    asyncio.run(
        linkedin_outreach_workflow(
            company_username="murex",
            headline_search_term="talent",
        )
    )


if __name__ == "__main__":
    run()
