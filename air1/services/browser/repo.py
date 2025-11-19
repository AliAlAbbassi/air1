from typing import Optional
from prisma import Prisma
from prisma.models import Lead, LinkedinProfile, LinkedinCompanyMember
from air1.db.prisma_client import get_prisma
from air1.services.browser.linkedin_profile import (
    Lead as LeadData,
    LinkedinProfile as LinkedinProfileData,
)
from air1.services.browser.prisma_models import CompanyLeadRecord
from air1.db.sql_loader import linkedin_queries, linkedin_company_queries, with_params
from loguru import logger


async def insert_lead(lead: LeadData) -> tuple[bool, int | None]:
    try:
        prisma = await get_prisma()

        sql, params = with_params(
            linkedin_queries["insert_lead"],
            lead.first_name,
            lead.full_name,
            lead.email,
            lead.phone_number,
        )
        results = await prisma.query_raw(sql, *params)

        if results and len(results) > 0:
            return True, results[0]["lead_id"]
        return False, None
    except Exception as e:
        logger.error(f"Failed to insert lead: {e}")
        return False, None


async def insert_linkedin_profile(
    profile: LinkedinProfileData, lead_id: int
) -> int | None:
    try:
        if not profile.username:
            logger.error("Username is required for LinkedIn profile insertion")
            return None

        logger.info(
            f"Inserting LinkedIn profile for lead_id={lead_id}, username={profile.username}"
        )

        prisma = await get_prisma()
        sql, params = with_params(
            linkedin_queries["insert_linkedin_profile"],
            lead_id,
            profile.username,
            profile.location,
            profile.headline,
            profile.about,
        )
        results = await prisma.query_raw(sql, *params)

        if results and len(results) > 0:
            profile_id = results[0]["linkedin_profile_id"]
            logger.info(
                f"LinkedIn profile insertion result: linkedin_profile_id={profile_id}"
            )
            return profile_id
        return None
    except Exception as e:
        logger.error(
            f"Failed to insert linkedin profile for lead_id={lead_id}, username={profile.username}: {e}"
        )
        return None


async def get_linkedin_profile_by_username(username: str) -> LinkedinProfile | None:
    try:
        prisma = await get_prisma()
        sql, params = with_params(
            linkedin_queries["get_linkedin_profile_by_username"], username
        )
        results = await prisma.query_raw(sql, *params)

        if results and len(results) > 0:
            return LinkedinProfile(**results[0])
        return None
    except Exception as e:
        logger.error(f"Failed to get LinkedIn profile for username {username}: {e}")
        return None


async def get_company_members_by_username(username: str) -> list[LinkedinCompanyMember]:
    try:
        prisma = await get_prisma()
        sql, params = with_params(
            linkedin_company_queries["get_company_members_by_username"], username
        )
        results = await prisma.query_raw(sql, *params)

        return [LinkedinCompanyMember(**row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get company members for username {username}: {e}")
        return []


async def get_company_member_by_profile_and_username(
    linkedin_profile_id: int, username: str
) -> LinkedinCompanyMember | None:
    try:
        prisma = await get_prisma()
        sql, params = with_params(
            linkedin_company_queries["get_company_member_by_profile_and_username"],
            linkedin_profile_id,
            username,
        )
        results = await prisma.query_raw(sql, *params)

        if results and len(results) > 0:
            return LinkedinCompanyMember(**results[0])
        return None
    except Exception as e:
        logger.error(
            f"Failed to get company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )
        return None


async def insert_linkedin_company_member(
    linkedin_profile_id: int, username: str, title: str | None = None
):
    try:
        if not username:
            logger.error("Username is required for company member insertion")
            return None

        logger.info(
            f"Inserting company member for linkedin_profile_id={linkedin_profile_id}, username={username}, title={title}"
        )

        prisma = await get_prisma()
        sql, params = with_params(
            linkedin_company_queries["insert_linkedin_company_member"],
            linkedin_profile_id,
            username,
            title,
        )
        await prisma.query_raw(sql, *params)

        logger.info(
            f"Company member insertion successful for linkedin_profile_id={linkedin_profile_id}, username={username}"
        )
    except Exception as e:
        logger.error(
            f"Failed to insert company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )


async def save_lead_complete(
    lead: LeadData,
    profile: LinkedinProfileData,
    username: str | None = None,
    title: str | None = None,
) -> tuple[bool, int | None]:
    try:
        prisma = await get_prisma()

        async with prisma.tx() as transaction:
            # Insert lead using raw SQL
            lead_sql, lead_params = with_params(
                linkedin_queries["insert_lead"],
                lead.first_name,
                lead.full_name,
                lead.email,
                lead.phone_number,
            )
            lead_results = await transaction.query_raw(lead_sql, *lead_params)

            if not lead_results or len(lead_results) == 0:
                return False, None

            lead_id = lead_results[0]["lead_id"]

            # Insert LinkedIn profile using raw SQL
            profile_sql, profile_params = with_params(
                linkedin_queries["insert_linkedin_profile"],
                lead_id,
                profile.username,
                profile.location,
                profile.headline,
                profile.about,
            )
            profile_results = await transaction.query_raw(profile_sql, *profile_params)

            if not profile_results or len(profile_results) == 0:
                return False, None

            profile_id = profile_results[0]["linkedin_profile_id"]

            # Insert company member if username provided
            if username:
                company_sql, company_params = with_params(
                    linkedin_company_queries["insert_linkedin_company_member"],
                    profile_id,
                    username,
                    title,
                )
                await transaction.query_raw(company_sql, *company_params)

            return True, lead_id
    except Exception as e:
        logger.error(f"Failed to save lead complete: {e}")
        return False, None


async def get_company_leads_by_headline(
    company_username: str, search_term: str
) -> list[CompanyLeadRecord]:
    """Get company leads by headline text using raw SQL (complex join query)"""
    try:
        prisma = await get_prisma()

        sql, params = with_params(
            linkedin_queries["get_company_leads_by_headline"],
            company_username,
            search_term,
        )
        results = await prisma.query_raw(sql, *params)

        return [CompanyLeadRecord(**row) for row in results]
    except Exception as e:
        logger.error(
            f"Failed to get company leads by headline for {company_username}: {e}"
        )
        return []


async def get_company_leads(company_username: str) -> list[CompanyLeadRecord]:
    """Get all leads for a company using raw SQL (complex join query)"""
    try:
        prisma = await get_prisma()

        sql, params = with_params(
            linkedin_queries["get_company_leads"], company_username
        )
        results = await prisma.query_raw(sql, *params)

        return [CompanyLeadRecord(**row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get company leads for {company_username}: {e}")
        raise RuntimeError(
            f"Repo error retrieving company leads for '{company_username}': {str(e)}"
        ) from e
