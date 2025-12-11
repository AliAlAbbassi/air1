"""Repository functions for account data."""

from typing import Optional
from loguru import logger
from prisma.errors import PrismaError

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import account_queries as queries
from air1.services.outreach.exceptions import QueryError


async def get_account_by_user_id(user_id: int) -> Optional[dict]:
    """Get account data by user ID."""
    try:
        prisma = await get_prisma()
        result = await queries.get_account_by_user_id(prisma, user_id=user_id)
        return result
    except PrismaError as e:
        logger.error(f"Database error getting account: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting account: {e}")
        raise QueryError(f"Unexpected error getting account: {e}") from e


async def update_user_profile(
    user_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    timezone: Optional[str] = None,
    meeting_link: Optional[str] = None,
) -> bool:
    """Update user profile fields."""
    try:
        prisma = await get_prisma()
        await queries.update_user_profile(
            prisma,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            timezone=timezone,
            meeting_link=meeting_link,
        )
        return True
    except PrismaError as e:
        logger.error(f"Database error updating profile: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating profile: {e}")
        raise QueryError(f"Unexpected error updating profile: {e}") from e
