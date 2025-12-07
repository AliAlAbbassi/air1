"""Repository functions for onboarding data persistence."""
from typing import Optional
from loguru import logger
from prisma.errors import PrismaError

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import onboarding_queries as queries
from air1.services.outreach.exceptions import QueryError


class UserExistsError(Exception):
    """Raised when user with email already exists."""
    pass


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email address."""
    try:
        prisma = await get_prisma()
        result = await queries.get_user_by_email(prisma, email=email)
        return result
    except PrismaError as e:
        logger.error(f"Database error getting user by email: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting user by email: {e}")
        raise QueryError(f"Unexpected error getting user by email: {e}") from e


async def create_user_with_onboarding(
    email: str,
    first_name: str,
    last_name: str,
    full_name: str,
    auth_method: str,
    password_hash: Optional[str],
    timezone: str,
    meeting_link: str,
    linkedin_connected: bool,
    company_name: str,
    company_description: str,
    company_website: str,
    company_industry: str,
    company_linkedin_url: str,
    company_size: str,
    product_name: str,
    product_url: str,
    product_description: str,
    product_icp: str,
    product_competitors: Optional[str],
    writing_style_template: Optional[str],
    writing_style_dos: list[str],
    writing_style_donts: list[str],
) -> tuple[bool, Optional[int]]:
    """
    Create a new user with all onboarding data in a transaction.
    
    Returns:
        Tuple of (success: bool, user_id: int | None)
    """
    try:
        prisma = await get_prisma()
        
        async with prisma.tx() as tx:
            # Insert user
            user_result = await queries.insert_user(
                tx,
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                auth_method=auth_method,
                first_name=first_name,
                last_name=last_name,
                timezone=timezone,
                meeting_link=meeting_link,
                linkedin_connected=linkedin_connected,
            )
            
            if not user_result:
                return False, None
            
            user_id = user_result["userId"]
            
            # Extract linkedin username from URL
            linkedin_username = None
            if company_linkedin_url:
                import re
                match = re.search(r"linkedin\.com/company/([^/?]+)", company_linkedin_url)
                if match:
                    linkedin_username = match.group(1)
            
            # Insert company
            await queries.insert_user_company(
                tx,
                name=company_name,
                linkedin_username=linkedin_username,
                website=company_website,
                industry=company_industry,
                size=company_size,
                description=company_description,
                user_id=user_id,
            )
            
            # Insert product
            await queries.insert_user_product(
                tx,
                user_id=user_id,
                name=product_name,
                website_url=product_url,
                description=product_description,
                target_icp=product_icp,
                competitors=product_competitors,
            )
            
            # Insert writing style
            await queries.insert_user_writing_style(
                tx,
                user_id=user_id,
                name="Default",
                tone=None,
                dos=writing_style_dos,
                donts=writing_style_donts,
                selected_template=writing_style_template,
            )
            
            return True, user_id
            
    except PrismaError as e:
        error_str = str(e)
        if "unique constraint" in error_str.lower() or "duplicate" in error_str.lower():
            logger.warning(f"User with email {email} already exists")
            raise UserExistsError(f"User with email {email} already exists")
        logger.error(f"Database error creating user with onboarding: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error creating user with onboarding: {e}")
        raise QueryError(f"Unexpected error creating user with onboarding: {e}") from e
