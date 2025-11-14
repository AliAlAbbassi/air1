import aiosql
import os
from air1.db.db import db
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile
from loguru import logger

# Load queries from SQL files
query_dir = os.path.join(os.path.dirname(__file__), "..", "..", "db", "query")
queries = aiosql.from_path(query_dir, "asyncpg")


async def insert_lead(lead: Lead, conn=None) -> tuple[bool, int | None]:
    try:
        # Use the provided connection or get the pool
        db_conn = conn if conn else await db.get_pool()
        result = await queries.insert_lead(
            db_conn,
            first_name=lead.first_name,
            full_name=lead.full_name,
            email=lead.email,
            phone_number=lead.phone_number,
        )
        # aiosql with ^ operator should return just the value
        # but with asyncpg it returns a Record, so get the first column
        lead_id = result[0] if result else None
        return True, lead_id
    except Exception as e:
        logger.error(f"Failed to insert lead: {e}")
        return False, None


async def insert_linkedin_profile(profile: LinkedinProfile, lead_id: int, conn=None):
    try:
        # Use the provided connection or get the pool
        db_conn = conn if conn else await db.get_pool()
        result = await queries.insert_linkedin_profile(
            db_conn,
            lead_id=lead_id,
            linkedin_url=profile.linkedin_url,
            location=profile.location,
            headline=profile.headline,
            about=profile.about,
        )
        # Get first column (linkedin_profile_id)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Failed to insert linkedin profile: {e}")
        return None


async def insert_linkedin_company_member(
        linkedin_profile_id: int, username: str, title: str = None, conn=None
):
    try:
        # Use the provided connection or get the pool
        db_conn = conn if conn else await db.get_pool()
        await queries.insert_linkedin_company_member(
            db_conn,
            linkedin_profile_id=linkedin_profile_id,
            username=username,
            title=title,
        )
    except Exception as e:
        logger.error(f"Failed to insert company member: {e}")


async def save_lead_complete(
        lead: Lead,
        profile: LinkedinProfile,
        username: str = None,
        title: str = None
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

                linkedin_profile_id = await insert_linkedin_profile(profile, lead_id, conn)
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
