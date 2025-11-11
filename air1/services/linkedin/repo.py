import aiosql
import os
from air1.db.db import db
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile

# Load queries from SQL files
query_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'query')
queries = aiosql.from_path(query_dir, "asyncpg")


async def insert_lead(lead: Lead) -> tuple[bool, int | None]:
    try:
        async with db.pool.acquire() as conn:
            result = await queries.insert_lead(conn, lead.first_name, lead.full_name, lead.email, lead.phone_number)
            lead_id = result  # aiosql returns the inserted/updated record
            return True, lead_id
    except Exception:
        return False, None


async def insert_linkedin_profile(profile: LinkedinProfile, lead_id: int):
    try:
        async with db.pool.acquire() as conn:
            result = await queries.insert_linkedin_profile(conn, lead_id, profile.linkedin_url, profile.location, profile.headline, profile.about)
            return result  # Return the linkedin_profile_id
    except Exception:
        return None


async def insert_linkedin_company_member(linkedin_profile_id: int, company_url: str, company_name: str = None):
    async with db.pool.acquire() as conn:
        await queries.insert_linkedin_company_member(conn, linkedin_profile_id, company_url, company_name)
