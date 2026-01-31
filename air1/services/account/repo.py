"""Repository functions for admin/agency data persistence.

These are low-level database operations for agency management.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from prisma.errors import PrismaError

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import admin_queries as queries
from air1.services.outreach.exceptions import QueryError

# ============================================================================
# AGENCY & MEMBER FUNCTIONS
# ============================================================================


async def get_agency_by_member_user_id(user_id: int) -> Optional[dict]:
    """Get agency details for a user based on their membership."""
    try:
        prisma = await get_prisma()
        result = await queries.get_agency_by_member_user_id(prisma, user_id=user_id)
        return result
    except PrismaError as e:
        logger.error(f"Database error getting agency for user_id={user_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting agency for user_id={user_id}: {e}")
        raise QueryError(
            f"Unexpected error getting agency for user_id={user_id}: {e}"
        ) from e


async def get_agency_members(agency_id: int) -> list[dict]:
    """Get all members in an agency."""
    try:
        prisma = await get_prisma()
        results = await queries.get_agency_members(prisma, agency_id=agency_id)
        return results or []
    except PrismaError as e:
        logger.error(f"Database error getting members for agency_id={agency_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting members for agency_id={agency_id}: {e}")
        raise QueryError(
            f"Unexpected error getting members for agency_id={agency_id}: {e}"
        ) from e


async def get_agency_used_seats(agency_id: int) -> int:
    """Get the number of used seats in an agency."""
    try:
        prisma = await get_prisma()
        result = await queries.get_agency_used_seats(prisma, agency_id=agency_id)
        return result or 0
    except PrismaError as e:
        logger.error(
            f"Database error getting seat count for agency_id={agency_id}: {e}"
        )
        return 0
    except Exception as e:
        logger.error(
            f"Unexpected error getting seat count for agency_id={agency_id}: {e}"
        )
        raise QueryError(
            f"Unexpected error getting seat count for agency_id={agency_id}: {e}"
        ) from e


async def get_member_by_id(member_id: int) -> Optional[dict]:
    """Get a specific member by ID."""
    try:
        prisma = await get_prisma()
        result = await queries.get_member_by_id(prisma, member_id=member_id)
        return result
    except PrismaError as e:
        logger.error(f"Database error getting member_id={member_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting member_id={member_id}: {e}")
        raise QueryError(f"Unexpected error getting member_id={member_id}: {e}") from e


async def get_member_by_email(agency_id: int, email: str) -> Optional[dict]:
    """Get a member by email within an agency."""
    try:
        prisma = await get_prisma()
        result = await queries.get_member_by_email(
            prisma, agency_id=agency_id, email=email
        )
        return result
    except PrismaError as e:
        logger.error(f"Database error getting member by email={email}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting member by email={email}: {e}")
        raise QueryError(
            f"Unexpected error getting member by email={email}: {e}"
        ) from e


async def insert_agency_member(agency_id: int, email: str, role: str) -> Optional[dict]:
    """Insert a new agency member (for invites)."""
    try:
        prisma = await get_prisma()
        result = await queries.insert_agency_member(
            prisma, agency_id=agency_id, email=email, role=role
        )
        if result:
            logger.info(f"Created agency member: email={email}, role={role}")
        return result
    except PrismaError as e:
        logger.error(f"Database error inserting member email={email}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error inserting member email={email}: {e}")
        raise QueryError(f"Unexpected error inserting member email={email}: {e}") from e


async def update_member_role(member_id: int, role: str) -> Optional[dict]:
    """Update a member's role."""
    try:
        prisma = await get_prisma()
        result = await queries.update_member_role(
            prisma, member_id=member_id, role=role
        )
        if result:
            logger.info(f"Updated member_id={member_id} role to {role}")
        return result
    except PrismaError as e:
        logger.error(f"Database error updating role for member_id={member_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error updating role for member_id={member_id}: {e}")
        raise QueryError(
            f"Unexpected error updating role for member_id={member_id}: {e}"
        ) from e


async def delete_member(member_id: int) -> bool:
    """Delete a member from agency."""
    try:
        prisma = await get_prisma()
        await queries.delete_member(prisma, member_id=member_id)
        logger.info(f"Deleted member_id={member_id}")
        return True
    except PrismaError as e:
        logger.error(f"Database error deleting member_id={member_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting member_id={member_id}: {e}")
        raise QueryError(f"Unexpected error deleting member_id={member_id}: {e}") from e


async def update_member_joined(member_id: int, user_id: int, name: str) -> bool:
    """Update member status when they accept invite."""
    try:
        prisma = await get_prisma()
        await queries.update_member_joined(
            prisma, member_id=member_id, user_id=user_id, name=name
        )
        logger.info(f"Member {member_id} joined as user_id={user_id}")
        return True
    except PrismaError as e:
        logger.error(
            f"Database error updating member joined for member_id={member_id}: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error updating member joined for member_id={member_id}: {e}"
        )
        raise QueryError(f"Unexpected error updating member joined: {e}") from e


# ============================================================================
# INVITE FUNCTIONS
# ============================================================================


def generate_invite_token() -> str:
    """Generate a secure random invite token."""
    return secrets.token_urlsafe(32)


async def create_invite(
    member_id: Optional[int] = None,
    client_id: Optional[int] = None,
    expires_in_days: int = 7,
) -> Optional[dict]:
    """Create an invite token for a member or client."""
    try:
        token = generate_invite_token()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        prisma = await get_prisma()
        result = await queries.create_invite(
            prisma,
            member_id=member_id,
            client_id=client_id,
            token=token,
            expires_at=expires_at.isoformat(),
        )
        if result:
            logger.info(
                f"Created invite token for member_id={member_id}, client_id={client_id}"
            )
        return result
    except PrismaError as e:
        logger.error(f"Database error creating invite: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating invite: {e}")
        raise QueryError(f"Unexpected error creating invite: {e}") from e


async def get_invite_by_token(token: str) -> Optional[dict]:
    """Get invite details by token."""
    try:
        prisma = await get_prisma()
        result = await queries.get_invite_by_token(prisma, token=token)
        return result
    except PrismaError as e:
        logger.error(f"Database error getting invite by token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting invite by token: {e}")
        raise QueryError(f"Unexpected error getting invite by token: {e}") from e


async def delete_invite(invite_id: int) -> bool:
    """Delete an invite (consumed or expired)."""
    try:
        prisma = await get_prisma()
        await queries.delete_invite(prisma, invite_id=invite_id)
        return True
    except PrismaError as e:
        logger.error(f"Database error deleting invite_id={invite_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting invite_id={invite_id}: {e}")
        raise QueryError(f"Unexpected error deleting invite_id={invite_id}: {e}") from e


async def delete_invites_by_member(member_id: int) -> bool:
    """Delete all invites for a member."""
    try:
        prisma = await get_prisma()
        await queries.delete_invites_by_member(prisma, member_id=member_id)
        return True
    except PrismaError as e:
        logger.error(f"Database error deleting invites for member_id={member_id}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error deleting invites for member_id={member_id}: {e}"
        )
        raise QueryError(f"Unexpected error deleting invites: {e}") from e


# ============================================================================
# CLIENT FUNCTIONS
# ============================================================================


async def get_agency_clients(
    agency_id: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """Get all clients for an agency, optionally filtered."""
    try:
        prisma = await get_prisma()
        if status is None and search is None:
            results = await queries.get_agency_clients(prisma, agency_id=agency_id)
        else:
            results = await queries.get_agency_clients_filtered(
                prisma, agency_id=agency_id, status=status, search=search
            )
        return results or []
    except PrismaError as e:
        logger.error(f"Database error getting clients for agency_id={agency_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting clients for agency_id={agency_id}: {e}")
        raise QueryError(f"Unexpected error getting clients: {e}") from e


async def count_agency_clients(
    agency_id: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> int:
    """Count clients for an agency, optionally filtered."""
    try:
        prisma = await get_prisma()
        result = await queries.count_agency_clients(
            prisma, agency_id=agency_id, status=status, search=search
        )
        return result or 0
    except PrismaError as e:
        logger.error(f"Database error counting clients for agency_id={agency_id}: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error counting clients: {e}")
        raise QueryError(f"Unexpected error counting clients: {e}") from e


async def get_client_by_id(client_id: int) -> Optional[dict]:
    """Get a specific client by ID."""
    try:
        prisma = await get_prisma()
        result = await queries.get_client_by_id(prisma, client_id=client_id)
        return result
    except PrismaError as e:
        logger.error(f"Database error getting client_id={client_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting client_id={client_id}: {e}")
        raise QueryError(f"Unexpected error getting client: {e}") from e


async def insert_client(
    agency_id: int,
    name: str,
    admin_email: str,
    plan: str,
) -> Optional[dict]:
    """Create a new client."""
    try:
        prisma = await get_prisma()
        result = await queries.insert_client(
            prisma, agency_id=agency_id, name=name, admin_email=admin_email, plan=plan
        )
        if result:
            logger.info(f"Created client: name={name}, admin_email={admin_email}")
        return result
    except PrismaError as e:
        logger.error(f"Database error inserting client name={name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error inserting client: {e}")
        raise QueryError(f"Unexpected error inserting client: {e}") from e


async def update_client(
    client_id: int,
    name: Optional[str] = None,
    plan: Optional[str] = None,
) -> Optional[dict]:
    """Update client details."""
    try:
        prisma = await get_prisma()
        result = await queries.update_client(
            prisma, client_id=client_id, name=name, plan=plan
        )
        if result:
            logger.info(f"Updated client_id={client_id}")
        return result
    except PrismaError as e:
        logger.error(f"Database error updating client_id={client_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error updating client: {e}")
        raise QueryError(f"Unexpected error updating client: {e}") from e


async def delete_client(client_id: int) -> bool:
    """Delete a client."""
    try:
        prisma = await get_prisma()
        await queries.delete_client(prisma, client_id=client_id)
        logger.info(f"Deleted client_id={client_id}")
        return True
    except PrismaError as e:
        logger.error(f"Database error deleting client_id={client_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting client: {e}")
        raise QueryError(f"Unexpected error deleting client: {e}") from e


async def get_client_team(client_id: int) -> list[dict]:
    """Get team members for a client."""
    try:
        prisma = await get_prisma()
        results = await queries.get_client_team(prisma, client_id=client_id)
        return results or []
    except PrismaError as e:
        logger.error(f"Database error getting team for client_id={client_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting client team: {e}")
        raise QueryError(f"Unexpected error getting client team: {e}") from e


# ============================================================================
# IMPERSONATION FUNCTIONS
# ============================================================================


async def create_impersonation_token(
    client_id: int,
    member_id: int,
    expires_in_hours: int = 1,
) -> Optional[dict]:
    """Create an impersonation token for client access."""
    try:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        prisma = await get_prisma()
        result = await queries.create_impersonation_token(
            prisma,
            client_id=client_id,
            member_id=member_id,
            token=token,
            expires_at=expires_at.isoformat(),
        )
        if result:
            logger.info(
                f"Created impersonation token for client_id={client_id} by member_id={member_id}"
            )
        return result
    except PrismaError as e:
        logger.error(f"Database error creating impersonation token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating impersonation token: {e}")
        raise QueryError(f"Unexpected error creating impersonation token: {e}") from e


async def get_impersonation_token(token: str) -> Optional[dict]:
    """Validate an impersonation token."""
    try:
        prisma = await get_prisma()
        result = await queries.get_impersonation_token(prisma, token=token)
        return result
    except PrismaError as e:
        logger.error(f"Database error validating impersonation token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating impersonation token: {e}")
        raise QueryError(f"Unexpected error validating impersonation token: {e}") from e


async def delete_impersonation_token(token_id: int) -> bool:
    """Delete an impersonation token (after use)."""
    try:
        prisma = await get_prisma()
        await queries.delete_impersonation_token(prisma, token_id=token_id)
        return True
    except PrismaError as e:
        logger.error(f"Database error deleting impersonation token_id={token_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting impersonation token: {e}")
        raise QueryError(f"Unexpected error deleting impersonation token: {e}") from e
