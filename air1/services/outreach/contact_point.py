"""
ContactPoint map with contact point type as the key and type id as the value
"""

from loguru import logger

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import outreach_queries as queries
from air1.services.outreach.repo import insert_contact_point

# Contact point type IDs - should match your database
CONTACT_POINT_TYPES = {
    "linkedin_connection": 1,
    "email_sent": 2,
    "phone_call": 3,
}


async def insert_linkedin_connection(lead_id: int) -> bool:
    """
    Insert a LinkedIn connection contact point for a lead.

    Args:
        lead_id: The ID of the lead to track the connection for

    Returns:
        bool: True if the contact point was inserted successfully, False otherwise
    """
    try:
        await insert_contact_point(
            lead_id=lead_id,
            contact_point_type_id=CONTACT_POINT_TYPES["linkedin_connection"],
        )
        logger.info(f"LinkedIn connection contact point inserted for lead_id={lead_id}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to insert LinkedIn connection contact point for lead_id={lead_id}: {e}"
        )
        return False


async def has_linkedin_connection(username: str) -> bool:
    """
    Check if we've already sent a LinkedIn connection request to this profile.

    Args:
        username: LinkedIn profile username (e.g., 'john-doe-123')

    Returns:
        bool: True if a connection request was already sent, False otherwise
    """
    try:
        prisma = await get_prisma()
        result = await queries.has_linkedin_connection_by_username(
            prisma, username=username
        )
        return result.get("exists", False) if result else False
    except Exception as e:
        logger.error(f"Error checking connection status for {username}: {e}")
        return False
