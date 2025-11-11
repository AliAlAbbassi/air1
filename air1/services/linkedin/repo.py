import aiosql
import os
from air1.db.db import get_pool
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile
from loguru import logger

# Load queries from SQL files
query_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'query')
queries = aiosql.from_path(query_dir, "asyncpg")


async def insert_lead(lead: Lead) -> tuple[bool, int | None]:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await queries.insert_lead(conn,
                first_name=lead.first_name,
                full_name=lead.full_name,
                email=lead.email,
                phone_number=lead.phone_number)
            # aiosql with ^ operator should return just the value
            # but with asyncpg it returns a Record, so get the first column
            lead_id = result[0] if result else None
            return True, lead_id
    except Exception as e:
        logger.error(f"Failed to insert lead: {e}")
        return False, None


async def insert_linkedin_profile(profile: LinkedinProfile, lead_id: int):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await queries.insert_linkedin_profile(conn,
                lead_id=lead_id,
                linkedin_url=profile.linkedin_url,
                location=profile.location,
                headline=profile.headline,
                about=profile.about)
            # Get first column (linkedin_profile_id)
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Failed to insert linkedin profile: {e}")
        return None


async def insert_linkedin_company_member(linkedin_profile_id: int, company_url: str, company_name: str = None):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await queries.insert_linkedin_company_member(conn,
                linkedin_profile_id=linkedin_profile_id,
                company_url=company_url,
                company_name=company_name)
    except Exception as e:
        logger.error(f"Failed to insert company member: {e}")