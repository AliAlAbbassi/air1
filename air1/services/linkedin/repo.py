import aiosql
import os
from air1.db.db import db
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile
from loguru import logger

query_dir = os.path.join(os.path.dirname(__file__), "..", "..", "db", "query")
queries = aiosql.from_path(query_dir, "asyncpg")


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
            logger.error(f"Username is required for LinkedIn profile insertion")
            return None

        logger.info(
            f"Inserting LinkedIn profile for lead_id={lead_id}, username={username}"
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
            f"Failed to insert linkedin profile for lead_id={lead_id}, username={username}: {e}"
        )
        return None


async def get_linkedin_profile_by_username(username: str) -> dict | None:
    """Fetch LinkedIn profile by username"""
    try:
        pool = await db.get_pool()
        result = await queries.get_linkedin_profile_by_username(pool, username=username)
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"Failed to get LinkedIn profile for username {username}: {e}")
        return None


async def insert_linkedin_company_member(
    linkedin_profile_id: int, company_url: str, company_name: str = None, conn=None
):
    try:
        # Use the provided connection or get the pool
        db_conn = conn if conn else await db.get_pool()
        await queries.insert_linkedin_company_member(
            db_conn,
            linkedin_profile_id=linkedin_profile_id,
            company_url=company_url,
            company_name=company_name,
        )
    except Exception as e:
        logger.error(f"Failed to insert company member: {e}")


async def save_lead_complete(
    lead: Lead,
    profile: LinkedinProfile,
    company_url: str = None,
    company_name: str = None,
) -> tuple[bool, int | None]:
    """Save lead with profile and company association in one transaction."""
    try:
        # Get the pool first, then acquire a connection
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                success, lead_id = await insert_lead(lead, conn)
                if not success:
                    return False, None

                linkedin_profile_id = await insert_linkedin_profile(
                    profile, lead_id, conn
                )
                if not linkedin_profile_id:
                    return False, None

                if company_url and linkedin_profile_id:
                    await insert_linkedin_company_member(
                        linkedin_profile_id, company_url, company_name, conn
                    )

                return True, lead_id
    except Exception as e:
        logger.error(f"Failed to save lead complete: {e}")
        return False, None
