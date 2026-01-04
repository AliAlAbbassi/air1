"""Admin service for agency management.

This service contains business logic for:
- Team member management (invite, remove, update roles)
- Client account management (create, update, remove)
- Impersonation for support access
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from loguru import logger

from air1.services.admin import repo


class AdminError(Enum):
    """Admin operation error types."""
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ALREADY_INVITED = "ALREADY_INVITED"
    SEAT_LIMIT_REACHED = "SEAT_LIMIT_REACHED"
    CANNOT_REMOVE_OWNER = "CANNOT_REMOVE_OWNER"
    CANNOT_CHANGE_OWNER_ROLE = "CANNOT_CHANGE_OWNER_ROLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class AdminResult:
    """Result of an admin operation."""
    success: bool
    data: Optional[dict] = None
    error: Optional[AdminError] = None
    message: Optional[str] = None


def _validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _validate_role(role: str, allow_owner: bool = False) -> bool:
    """Validate role value."""
    valid_roles = ['admin', 'manager']
    if allow_owner:
        valid_roles.append('owner')
    return role in valid_roles


def _validate_plan(plan: str) -> bool:
    """Validate plan value."""
    return plan in ['starter', 'pro', 'enterprise']


class AdminService:
    """Service for admin/agency operations."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the admin service.
        
        Args:
            base_url: Base URL for generating invite links. Defaults to APP_BASE_URL env var.
        """
        self.base_url = base_url or os.getenv("APP_BASE_URL", "http://localhost:3000")

    # =========================================================================
    # AUTHORIZATION
    # =========================================================================

    async def get_user_agency_context(self, user_id: int) -> Optional[dict]:
        """Get the agency context for a user (agency_id, role, etc).
        
        Returns None if user is not a member of any agency.
        """
        return await repo.get_agency_by_member_user_id(user_id)

    async def require_admin_access(self, user_id: int) -> AdminResult:
        """Check if user has admin/owner access to their agency.
        
        Returns AdminResult with agency context data on success.
        """
        context = await self.get_user_agency_context(user_id)
        
        if not context:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="You don't have permission to access this resource",
            )
        
        if context.get("role") not in ["owner", "admin"]:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="You don't have permission to access this resource",
            )
        
        return AdminResult(success=True, data=context)

    # =========================================================================
    # TEAM MANAGEMENT
    # =========================================================================

    async def get_team_members(self, agency_id: int) -> AdminResult:
        """Get all team members in the agency with seat info."""
        members = await repo.get_agency_members(agency_id)
        used_seats = await repo.get_agency_used_seats(agency_id)
        
        # Get agency for total seats
        # For now we'll just return the used_seats and assume total is from context
        return AdminResult(
            success=True,
            data={
                "members": members,
                "usedSeats": used_seats,
            },
        )

    async def invite_team_member(
        self,
        agency_id: int,
        total_seats: int,
        email: str,
        role: str,
    ) -> AdminResult:
        """Invite a new team member to the agency."""
        # Validate email
        if not _validate_email(email):
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Invalid email address",
            )

        # Validate role
        if not _validate_role(role):
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Invalid role. Must be 'admin' or 'manager'",
            )

        # Check if already invited
        existing = await repo.get_member_by_email(agency_id, email)
        if existing:
            return AdminResult(
                success=False,
                error=AdminError.ALREADY_INVITED,
                message="This email has already been invited",
            )

        # Check seat limit
        used_seats = await repo.get_agency_used_seats(agency_id)
        if used_seats >= total_seats:
            return AdminResult(
                success=False,
                error=AdminError.SEAT_LIMIT_REACHED,
                message="No available seats. Please upgrade your plan.",
            )

        # Create member record
        member = await repo.insert_agency_member(agency_id, email, role)
        if not member:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to create invitation",
            )

        member_id = member.get("member_id")

        # Create invite token
        invite = await repo.create_invite(member_id=member_id)
        if not invite:
            # Clean up member if invite creation fails
            await repo.delete_member(member_id)
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to create invitation link",
            )

        # TODO: Send invitation email
        logger.info(f"Created invitation for {email} with token: {invite.get('token')}")

        return AdminResult(
            success=True,
            data={
                "memberID": str(member_id),
                "email": email,
                "role": role,
                "status": "pending",
                "invitedAt": member.get("invited_at"),
            },
        )

    async def resend_invite(self, agency_id: int, member_id: int) -> AdminResult:
        """Resend invitation email to a pending team member."""
        # Get member
        member = await repo.get_member_by_id(member_id)
        if not member:
            return AdminResult(
                success=False,
                error=AdminError.NOT_FOUND,
                message="Team member not found",
            )

        # Verify member belongs to this agency
        if member.get("agency_id") != agency_id:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="Team member not found",
            )

        # Check if still pending
        if member.get("status") != "pending":
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Member has already joined",
            )

        # Delete old invites and create new one
        await repo.delete_invites_by_member(member_id)
        invite = await repo.create_invite(member_id=member_id)
        
        if not invite:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to create invitation link",
            )

        # TODO: Send invitation email
        logger.info(f"Resent invitation to {member.get('email')} with token: {invite.get('token')}")

        return AdminResult(
            success=True,
            data={"message": "Invitation resent"},
        )

    async def update_member_role(
        self,
        agency_id: int,
        member_id: int,
        new_role: str,
    ) -> AdminResult:
        """Update a team member's role."""
        # Validate role
        if not _validate_role(new_role):
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Invalid role. Must be 'admin' or 'manager'",
            )

        # Get member
        member = await repo.get_member_by_id(member_id)
        if not member:
            return AdminResult(
                success=False,
                error=AdminError.NOT_FOUND,
                message="Team member not found",
            )

        # Verify member belongs to this agency
        if member.get("agency_id") != agency_id:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="Team member not found",
            )

        # Cannot change owner's role
        if member.get("role") == "owner":
            return AdminResult(
                success=False,
                error=AdminError.CANNOT_CHANGE_OWNER_ROLE,
                message="Cannot change the owner's role",
            )

        # Update role
        result = await repo.update_member_role(member_id, new_role)
        if not result:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to update role",
            )

        return AdminResult(
            success=True,
            data={
                "memberID": str(member_id),
                "role": new_role,
                "updatedAt": result.get("updated_on"),
            },
        )

    async def remove_team_member(self, agency_id: int, member_id: int) -> AdminResult:
        """Remove a team member from the agency."""
        # Get member
        member = await repo.get_member_by_id(member_id)
        if not member:
            return AdminResult(
                success=False,
                error=AdminError.NOT_FOUND,
                message="Team member not found",
            )

        # Verify member belongs to this agency
        if member.get("agency_id") != agency_id:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="Team member not found",
            )

        # Cannot remove owner
        if member.get("role") == "owner":
            return AdminResult(
                success=False,
                error=AdminError.CANNOT_REMOVE_OWNER,
                message="Cannot remove the agency owner",
            )

        # Delete member and associated invites
        await repo.delete_invites_by_member(member_id)
        success = await repo.delete_member(member_id)
        
        if not success:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to remove team member",
            )

        return AdminResult(
            success=True,
            data={"message": "Team member removed"},
        )

    # =========================================================================
    # CLIENT MANAGEMENT
    # =========================================================================

    async def get_clients(
        self,
        agency_id: int,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> AdminResult:
        """Get all clients for the agency with optional filters."""
        # Normalize 'all' status to None (no filter)
        if status == "all":
            status = None

        clients = await repo.get_agency_clients(agency_id, status=status, search=search)
        total = await repo.count_agency_clients(agency_id, status=status, search=search)

        return AdminResult(
            success=True,
            data={
                "clients": clients,
                "total": total,
            },
        )

    async def create_client(
        self,
        agency_id: int,
        name: str,
        admin_email: str,
        plan: str,
    ) -> AdminResult:
        """Create a new client account."""
        # Validate email
        if not _validate_email(admin_email):
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Invalid email address",
            )

        # Validate plan
        if not _validate_plan(plan):
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Invalid plan. Must be 'starter', 'pro', or 'enterprise'",
            )

        # Validate name
        if not name or len(name.strip()) < 2:
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Client name is required",
            )

        # Create client
        client = await repo.insert_client(agency_id, name.strip(), admin_email, plan)
        if not client:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to create client",
            )

        client_id = client.get("client_id")

        # Create invite link
        invite = await repo.create_invite(client_id=client_id)
        invite_link = None
        if invite:
            token = invite.get("token")
            invite_link = f"{self.base_url}/setup?token={token}"

        return AdminResult(
            success=True,
            data={
                "clientID": str(client_id),
                "name": name.strip(),
                "adminEmail": admin_email,
                "status": "onboarding",
                "linkedinConnected": False,
                "plan": plan,
                "createdAt": client.get("created_on"),
                "inviteLink": invite_link,
            },
        )

    async def get_client(self, agency_id: int, client_id: int) -> AdminResult:
        """Get detailed information about a specific client."""
        client = await repo.get_client_by_id(client_id)
        if not client:
            return AdminResult(
                success=False,
                error=AdminError.NOT_FOUND,
                message="Client not found",
            )

        # Verify client belongs to this agency
        if client.get("agency_id") != agency_id:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="Client not found",
            )

        # Get client team
        team = await repo.get_client_team(client_id)

        return AdminResult(
            success=True,
            data={
                "clientID": str(client_id),
                "name": client.get("name"),
                "adminEmail": client.get("admin_email"),
                "status": client.get("status"),
                "linkedinConnected": client.get("linkedin_connected", False),
                "linkedinProfileUrl": client.get("linkedin_profile_url"),
                "plan": client.get("plan"),
                "lastActive": client.get("last_active"),
                "createdAt": client.get("created_on"),
                "stats": {
                    "totalCampaigns": client.get("total_campaigns", 0),
                    "totalProspects": client.get("total_prospects", 0),
                    "meetingsBooked": client.get("meetings_booked", 0),
                },
                "team": [
                    {
                        "teamMemberID": str(m.get("client_team_member_id")),
                        "name": m.get("name"),
                        "email": m.get("email"),
                        "role": m.get("role"),
                    }
                    for m in team
                ],
            },
        )

    async def update_client(
        self,
        agency_id: int,
        client_id: int,
        name: Optional[str] = None,
        plan: Optional[str] = None,
    ) -> AdminResult:
        """Update client account settings."""
        # Get client first
        client = await repo.get_client_by_id(client_id)
        if not client:
            return AdminResult(
                success=False,
                error=AdminError.NOT_FOUND,
                message="Client not found",
            )

        # Verify client belongs to this agency
        if client.get("agency_id") != agency_id:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="Client not found",
            )

        # Validate plan if provided
        if plan and not _validate_plan(plan):
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Invalid plan. Must be 'starter', 'pro', or 'enterprise'",
            )

        # Validate name if provided
        if name is not None and len(name.strip()) < 2:
            return AdminResult(
                success=False,
                error=AdminError.VALIDATION_ERROR,
                message="Client name is too short",
            )

        # Update client
        updated = await repo.update_client(client_id, name=name, plan=plan)
        if not updated:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to update client",
            )

        return AdminResult(
            success=True,
            data={
                "clientID": str(client_id),
                "name": updated.get("name"),
                "adminEmail": updated.get("admin_email"),
                "status": updated.get("status"),
                "linkedinConnected": updated.get("linkedin_connected", False),
                "plan": updated.get("plan"),
                "lastActive": updated.get("last_active"),
                "createdAt": updated.get("created_on"),
            },
        )

    async def remove_client(self, agency_id: int, client_id: int) -> AdminResult:
        """Remove a client account from the agency."""
        # Get client first
        client = await repo.get_client_by_id(client_id)
        if not client:
            return AdminResult(
                success=False,
                error=AdminError.NOT_FOUND,
                message="Client not found",
            )

        # Verify client belongs to this agency
        if client.get("agency_id") != agency_id:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="Client not found",
            )

        # Delete client
        success = await repo.delete_client(client_id)
        if not success:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to remove client",
            )

        return AdminResult(
            success=True,
            data={"message": "Client account removed"},
        )

    async def impersonate_client(
        self,
        agency_id: int,
        member_id: int,
        client_id: int,
    ) -> AdminResult:
        """Generate a temporary token to log in as the client."""
        # Get client first
        client = await repo.get_client_by_id(client_id)
        if not client:
            return AdminResult(
                success=False,
                error=AdminError.NOT_FOUND,
                message="Client not found",
            )

        # Verify client belongs to this agency
        if client.get("agency_id") != agency_id:
            return AdminResult(
                success=False,
                error=AdminError.FORBIDDEN,
                message="Client not found",
            )

        # Create impersonation token (1 hour expiry)
        token_data = await repo.create_impersonation_token(
            client_id=client_id,
            member_id=member_id,
        )
        
        if not token_data:
            return AdminResult(
                success=False,
                error=AdminError.INTERNAL_ERROR,
                message="Failed to create impersonation session",
            )

        token = token_data.get("token")
        expires_at = token_data.get("expires_at")
        impersonation_url = f"{self.base_url}/impersonate?token={token}"

        return AdminResult(
            success=True,
            data={
                "impersonationUrl": impersonation_url,
                "expiresAt": expires_at,
            },
        )

