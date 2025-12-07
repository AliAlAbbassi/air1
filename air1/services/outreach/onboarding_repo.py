"""Repository functions for onboarding data persistence."""
import re
from typing import Optional

from loguru import logger
from prisma.errors import PrismaError
from pydantic import BaseModel

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import onboarding_queries as queries
from air1.services.outreach.exceptions import QueryError


class UserExistsError(Exception):
    """Raised when user with email already exists."""

    pass


class CreateUserInput(BaseModel):
    """Input model for creating a user with onboarding data."""

    email: str
    first_name: str
    last_name: str
    full_name: str
    auth_method: str
    password_hash: Optional[str]
    timezone: str
    meeting_link: str
    linkedin_connected: bool
    company_name: str
    company_description: str
    company_website: str
    company_industry: str
    company_linkedin_url: str
    company_size: str
    product_name: str
    product_url: str
    product_description: str
    product_icp: str
    product_competitors: Optional[str]
    writing_style_template: Optional[str]
    writing_style_dos: list[str]
    writing_style_donts: list[str]


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


async def create_user_with_onboarding(data: CreateUserInput) -> tuple[bool, Optional[int]]:
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
                email=data.email,
                full_name=data.full_name,
                password_hash=data.password_hash,
                auth_method=data.auth_method,
                first_name=data.first_name,
                last_name=data.last_name,
                timezone=data.timezone,
                meeting_link=data.meeting_link,
                linkedin_connected=data.linkedin_connected,
            )

            if not user_result:
                return False, None

            user_id = user_result["userId"]

            # Extract linkedin username from URL
            linkedin_username = None
            if data.company_linkedin_url:
                match = re.search(
                    r"linkedin\.com/company/([^/?]+)", data.company_linkedin_url
                )
                if match:
                    linkedin_username = match.group(1)

            # Insert company
            await queries.insert_user_company(
                tx,
                name=data.company_name,
                linkedin_username=linkedin_username,
                website=data.company_website,
                industry=data.company_industry,
                size=data.company_size,
                description=data.company_description,
                user_id=user_id,
            )

            # Insert product
            await queries.insert_user_product(
                tx,
                user_id=user_id,
                name=data.product_name,
                website_url=data.product_url,
                description=data.product_description,
                target_icp=data.product_icp,
                competitors=data.product_competitors,
            )

            # Insert writing style
            await queries.insert_user_writing_style(
                tx,
                user_id=user_id,
                name="Default",
                tone=None,
                dos=data.writing_style_dos,
                donts=data.writing_style_donts,
                selected_template=data.writing_style_template,
            )

            return True, user_id

    except PrismaError as e:
        error_str = str(e)
        if "unique constraint" in error_str.lower() or "duplicate" in error_str.lower():
            logger.warning(f"User with email {data.email} already exists")
            raise UserExistsError(f"User with email {data.email} already exists")
        logger.error(f"Database error creating user with onboarding: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error creating user with onboarding: {e}")
        raise QueryError(f"Unexpected error creating user with onboarding: {e}") from e
