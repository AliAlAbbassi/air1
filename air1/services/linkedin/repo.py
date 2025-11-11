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
            result = await queries.insert_lead(conn,
                first_name=lead.first_name,
                full_name=lead.full_name,
                email=lead.email,
                phone_number=lead.phone_number)
            # Extract the lead_id from the Record object
            # asyncpg returns a Record object, access the value directly
            if hasattr(result, 'get'):
                lead_id = result.get('lead_id') or result[0]
            elif hasattr(result, '__getitem__'):
                lead_id = result['lead_id']
            else:
                lead_id = result
            return True, lead_id
    except Exception:
        return False, None


async def insert_linkedin_profile(profile: LinkedinProfile, lead_id: int):
    try:
        async with db.pool.acquire() as conn:
            result = await queries.insert_linkedin_profile(conn,
                lead_id=lead_id,
                linkedin_url=profile.linkedin_url,
                location=profile.location,
                headline=profile.headline,
                about=profile.about)
            # Extract the profile_id from the Record object
            if hasattr(result, 'get'):
                profile_id = result.get('linkedin_profile_id') or result[0]
            elif hasattr(result, '__getitem__'):
                profile_id = result['linkedin_profile_id']
            else:
                profile_id = result
            return profile_id
    except Exception:
        return None


async def insert_linkedin_company_member(linkedin_profile_id: int, company_url: str, company_name: str = None):
    async with db.pool.acquire() as conn:
        await queries.insert_linkedin_company_member(conn,
            linkedin_profile_id=linkedin_profile_id,
            company_url=company_url,
            company_name=company_name)
