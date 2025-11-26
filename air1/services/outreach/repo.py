from loguru import logger
from prisma.models import LinkedinCompanyMember, LinkedinProfile

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import outreach_queries as queries
from air1.services.outreach.linkedin_profile import (
    Lead as LeadData,
)
from air1.services.outreach.linkedin_profile import (
    LinkedinProfile as LinkedinProfileData,
)
from air1.services.outreach.prisma_models import CompanyLeadRecord


async def insert_lead(lead: LeadData) -> tuple[bool, int | None]:
    try:
        prisma = await get_prisma()

        result = await queries.insert_lead(
            prisma,
            first_name=lead.first_name,
            full_name=lead.full_name,
            email=lead.email,
            phone_number=lead.phone_number,
        )

        if result:
            return True, result["leadId"]
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
        result = await queries.insert_linkedin_profile(
            prisma,
            lead_id=int(lead_id),
            username=profile.username,
            location=profile.location,
            headline=profile.headline,
            about=profile.about,
        )

        if result:
            profile_id = result["linkedinProfileId"]
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
        result = await queries.get_linkedin_profile_by_username(
            prisma, username=username
        )

        if result:
            return LinkedinProfile(**result)
        return None
    except Exception as e:
        logger.error(f"Failed to get LinkedIn profile for username {username}: {e}")
        return None


async def get_company_members_by_username(username: str) -> list[LinkedinCompanyMember]:
    try:
        prisma = await get_prisma()
        results = await queries.get_company_members_by_username(
            prisma, username=username
        )

        return [LinkedinCompanyMember(**row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get company members for username {username}: {e}")
        return []


async def get_company_member_by_profile_and_username(
    linkedin_profile_id: int, username: str
) -> LinkedinCompanyMember | None:
    try:
        prisma = await get_prisma()
        result = await queries.get_company_member_by_profile_and_username(
            prisma, linkedin_profile_id=linkedin_profile_id, username=username
        )

        if result:
            return LinkedinCompanyMember(**result)
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
        await queries.insert_linkedin_company_member(
            prisma,
            linkedin_profile_id=linkedin_profile_id,
            username=username,
            title=title,
        )

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
            # Insert lead using aiosql
            lead_result = await queries.insert_lead(
                transaction,
                first_name=lead.first_name,
                full_name=lead.full_name,
                email=lead.email,
                phone_number=lead.phone_number,
            )

            if not lead_result:
                return False, None

            lead_id = lead_result["leadId"]

            # Insert LinkedIn profile using aiosql
            profile_result = await queries.insert_linkedin_profile(
                transaction,
                lead_id=int(lead_id),
                username=profile.username,
                location=profile.location,
                headline=profile.headline,
                about=profile.about,
            )

            if not profile_result:
                return False, None

            profile_id = profile_result["linkedinProfileId"]

            # Insert company member if username provided
            if username:
                await queries.insert_linkedin_company_member(
                    transaction,
                    linkedin_profile_id=profile_id,
                    username=username,
                    title=title,
                )

            return True, lead_id
    except Exception as e:
        logger.error(f"Failed to save lead complete: {e}")
        return False, None


async def get_company_leads_by_headline(
    company_username: str, search_term: str, limit: int = 10
) -> list[CompanyLeadRecord]:
    """Get company leads by headline text using raw SQL (complex join query)"""
    try:
        prisma = await get_prisma()

        results = await queries.get_company_leads_by_headline(
            prisma,
            company_username=company_username,
            search_term=search_term,
            limit=limit,
        )

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

        results = await queries.get_company_leads(
            prisma, company_username=company_username
        )

        return [CompanyLeadRecord(**row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get company leads for {company_username}: {e}")
        raise RuntimeError(
            f"Repo error retrieving company leads for '{company_username}': {str(e)}"
        ) from e


async def insert_contact_point(lead_id: int, contact_point_type_id: int) -> bool:
    try:
        logger.debug(f"Attempting to insert contact point for lead_id={lead_id}, type_id={contact_point_type_id}")
        prisma = await get_prisma()
        result = await queries.insert_contact_point(
            prisma,
            lead_id=lead_id,
            contact_point_type_id=contact_point_type_id,
        )

        if result and result.get("contact_point_id"):
            logger.info(
                f"Contact point inserted successfully: id={result['contact_point_id']}, lead_id={lead_id}, type_id={contact_point_type_id}"
            )
            return True
        else:
            logger.error(f"Insert contact point returned no result for lead_id={lead_id}")
            return False
    except Exception as e:
        logger.error(f"Failed to insert contact point for lead_id={lead_id}: {e}", exc_info=True)
        return False
