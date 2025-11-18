import aiosql
import os
from typing import Any
from air1.db.db import db
from air1.services.browser.linkedin_profile import Lead, LinkedinProfile
from air1.services.browser.models import (
    LinkedinProfileRecord,
    LinkedinCompanyMemberRecord,
    CompanyLeadRecord,
)
from loguru import logger
from typing import TypeVar, Type

T = TypeVar('T')

def to_pydantic_list(results, model_class: Type[T]) -> list[T]:
    """Convert database results to list of Pydantic models"""
    if not results:
        return []
    return [model_class(**dict(result)) for result in results]

def to_pydantic_single(result, model_class: Type[T]) -> T | None:
    """Convert single database result to Pydantic model"""
    if not result:
        return None
    return model_class(**dict(result))

query_dir = os.path.join(os.path.dirname(__file__), "..", "..", "db", "query")
queries: Any = aiosql.from_path(query_dir, "asyncpg")


async def insert_lead(lead: Lead, conn=None) -> tuple[bool, int | None]:
    try:
        db_conn = conn if conn else await db.get_pool()
        result = await queries.insert_lead(
            db_conn,
            first_name=lead.first_name,
            full_name=lead.full_name,
            email=lead.email,
            phone_number=lead.phone_number,
        )
        lead_id = result[0] if result else None
        return True, lead_id
    except Exception as e:
        logger.error(f"Failed to insert lead: {e}")
        return False, None


async def insert_linkedin_profile(profile: LinkedinProfile, lead_id: int, conn=None):
    try:
        db_conn = conn if conn else await db.get_pool()

        if not profile.username:
            logger.error("Username is required for LinkedIn profile insertion")
            return None

        logger.info(
            f"Inserting LinkedIn profile for lead_id={lead_id}, username={profile.username}"
        )
        result = await queries.insert_linkedin_profile(
            db_conn,
            lead_id=lead_id,
            username=profile.username,
            location=profile.location,
            headline=profile.headline,
            about=profile.about,
        )
        linkedin_profile_id = result[0] if result else None
        logger.info(
            f"LinkedIn profile insertion result: linkedin_profile_id={linkedin_profile_id}"
        )
        return linkedin_profile_id
    except Exception as e:
        logger.error(
            f"Failed to insert linkedin profile for lead_id={lead_id}, username={profile.username}: {e}"
        )
        return None


async def get_linkedin_profile_by_username(
    username: str,
) -> LinkedinProfileRecord | None:
    """Fetch LinkedIn profile by username"""
    try:
        pool = await db.get_pool()
        result = await queries.get_linkedin_profile_by_username(pool, username=username)
        return to_pydantic_single(result, LinkedinProfileRecord)
    except Exception as e:
        logger.error(f"Failed to get LinkedIn profile for username {username}: {e}")
        return None


async def get_company_members_by_username(
    username: str,
) -> list[LinkedinCompanyMemberRecord]:
    """Fetch all company members by username"""
    try:
        pool = await db.get_pool()
        results = await queries.get_company_members_by_username(pool, username=username)
        return to_pydantic_list(results, LinkedinCompanyMemberRecord)
    except Exception as e:
        logger.error(f"Failed to get company members for username {username}: {e}")
        return []


async def get_company_member_by_profile_and_username(
    linkedin_profile_id: int, username: str
) -> LinkedinCompanyMemberRecord | None:
    """Fetch specific company member by profile ID and username"""
    try:
        pool = await db.get_pool()
        result = await queries.get_company_member_by_profile_and_username(
            pool, linkedin_profile_id=linkedin_profile_id, username=username
        )
        return to_pydantic_single(result, LinkedinCompanyMemberRecord)
    except Exception as e:
        logger.error(
            f"Failed to get company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )
        return None


async def insert_linkedin_company_member(
    linkedin_profile_id: int, username: str, title: str | None = None, conn=None
):
    try:
        db_conn = conn if conn else await db.get_pool()

        if not username:
            logger.error("Username is required for company member insertion")
            return None

        logger.info(
            f"Inserting company member for linkedin_profile_id={linkedin_profile_id}, username={username}, title={title}"
        )
        await queries.insert_linkedin_company_member(
            db_conn,
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
    lead: Lead,
    profile: LinkedinProfile,
    username: str | None = None,
    title: str | None = None,
) -> tuple[bool, int | None]:
    """Save lead with profile and company association in one transaction."""
    try:
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                success, lead_id = await insert_lead(lead, conn)
                if not success or lead_id is None:
                    return False, None

                linkedin_profile_id = await insert_linkedin_profile(
                    profile, lead_id, conn
                )
                if not linkedin_profile_id:
                    return False, None

                if username and linkedin_profile_id:
                    await insert_linkedin_company_member(
                        linkedin_profile_id, username, title, conn
                    )

                return True, lead_id
    except Exception as e:
        logger.error(f"Failed to save lead complete: {e}")
        return False, None


async def get_company_leads_by_headline(
    company_username: str, search_term: str
) -> list[CompanyLeadRecord]:
    """Get company leads by headline text"""
    try:
        pool = await db.get_pool()
        results = await queries.search_company_leads_by_headline(
            pool, company_username=company_username, search_term=search_term
        )
        return to_pydantic_list(results, CompanyLeadRecord)
    except Exception as e:
        logger.error(
            f"Failed to search company leads by headline for {company_username}: {e}"
        )
        return []


async def get_company_leads(company_username: str) -> list[CompanyLeadRecord]:
    """Get all leads for a company"""
    try:
        pool = await db.get_pool()
        results = await queries.get_company_leads(
            pool, company_username=company_username
        )
        return to_pydantic_list(results, CompanyLeadRecord)
    except Exception as e:
        logger.error(f"Failed to get company leads for {company_username}: {e}")
        raise RuntimeError(
            f"Repo error retrieving company leads for '{company_username}': {str(e)}"
        ) from e
