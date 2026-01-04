"""Admin API routes for agency management.

All endpoints require:
1. Valid Clerk JWT token (authentication)
2. User must have 'owner' or 'admin' role in their agency (authorization)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from air1.api.auth import AuthUser, get_current_user
from air1.api.models.admin import (
    ClientDetailResponse,
    ClientListResponse,
    ClientStats,
    ClientSummary,
    ClientTeamMember,
    CreateClientRequest,
    CreateClientResponse,
    ErrorResponse,
    ImpersonateResponse,
    InviteTeamMemberRequest,
    InviteTeamMemberResponse,
    SuccessResponse,
    TeamListResponse,
    TeamMember,
    UpdateClientRequest,
    UpdateMemberRoleRequest,
    UpdateMemberRoleResponse,
)
from air1.services.admin.service import AdminError, AdminService
from air1.services.user.account_repo import get_account_by_clerk_id

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Service instance
admin_service = AdminService()


# Error status code mapping
ERROR_STATUS_CODES = {
    AdminError.UNAUTHORIZED: 401,
    AdminError.FORBIDDEN: 403,
    AdminError.NOT_FOUND: 404,
    AdminError.VALIDATION_ERROR: 400,
    AdminError.ALREADY_INVITED: 409,
    AdminError.SEAT_LIMIT_REACHED: 402,
    AdminError.CANNOT_REMOVE_OWNER: 403,
    AdminError.CANNOT_CHANGE_OWNER_ROLE: 403,
    AdminError.INTERNAL_ERROR: 500,
}


async def _get_user_id_from_clerk(clerk_id: str) -> int:
    """Get the internal user_id from clerk_id."""
    account = await get_account_by_clerk_id(clerk_id)
    if not account:
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "message": "User not found"},
        )
    return account["user_id"]


async def _require_admin(current_user: AuthUser) -> dict:
    """Verify user has admin access and return agency context."""
    user_id = await _get_user_id_from_clerk(current_user.user_id)
    result = await admin_service.require_admin_access(user_id)
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 403)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return result.data


# ============================================================================
# TEAM MANAGEMENT
# ============================================================================


@router.get(
    "/team",
    response_model=TeamListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
    },
)
async def get_team(current_user: AuthUser = Depends(get_current_user)):
    """Get all team members in the agency."""
    context = await _require_admin(current_user)
    
    agency_id = context["agency_id"]
    total_seats = context.get("total_seats", 10)  # Default if not in context
    
    result = await admin_service.get_team_members(agency_id)
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": "Failed to load team"},
        )
    
    # Transform members to response format
    members = [
        TeamMember(
            memberID=str(m.get("member_id")),
            name=m.get("name"),
            email=m.get("email"),
            role=m.get("role"),
            status=m.get("status"),
            avatarUrl=m.get("avatar_url"),
            invitedAt=m.get("invited_at"),
            joinedAt=m.get("joined_at"),
        )
        for m in result.data["members"]
    ]
    
    return TeamListResponse(
        members=members,
        totalSeats=total_seats,
        usedSeats=result.data["usedSeats"],
    )


@router.post(
    "/team/invite",
    response_model=InviteTeamMemberResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        402: {"model": ErrorResponse, "description": "Seat limit reached"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        409: {"model": ErrorResponse, "description": "Already invited"},
    },
)
async def invite_team_member(
    request: InviteTeamMemberRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Invite a new team member to the agency."""
    context = await _require_admin(current_user)
    
    agency_id = context["agency_id"]
    total_seats = context.get("total_seats", 10)
    
    result = await admin_service.invite_team_member(
        agency_id=agency_id,
        total_seats=total_seats,
        email=request.email,
        role=request.role,
    )
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return InviteTeamMemberResponse(
        memberID=result.data["memberID"],
        email=result.data["email"],
        role=result.data["role"],
        status=result.data["status"],
        invitedAt=result.data["invitedAt"],
    )


@router.delete(
    "/team/{member_id}",
    response_model=SuccessResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden / Cannot remove owner"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def remove_team_member(
    member_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Remove a team member from the agency."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.remove_team_member(agency_id, member_id)
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return SuccessResponse(success=True, message=result.data["message"])


@router.post(
    "/team/{member_id}/resend-invite",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def resend_invite(
    member_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Resend invitation email to a pending team member."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.resend_invite(agency_id, member_id)
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return SuccessResponse(success=True, message=result.data["message"])


@router.patch(
    "/team/{member_id}/role",
    response_model=UpdateMemberRoleResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden / Cannot change owner role"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def update_member_role(
    member_id: int,
    request: UpdateMemberRoleRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Update a team member's role."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.update_member_role(
        agency_id=agency_id,
        member_id=member_id,
        new_role=request.role,
    )
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return UpdateMemberRoleResponse(
        memberID=result.data["memberID"],
        role=result.data["role"],
        updatedAt=result.data["updatedAt"],
    )


# ============================================================================
# CLIENT MANAGEMENT
# ============================================================================


@router.get(
    "/clients",
    response_model=ClientListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
    },
)
async def get_clients(
    status: str = Query(default="all", description="Filter by status: active, onboarding, all"),
    search: str = Query(default=None, description="Search by client name or email"),
    current_user: AuthUser = Depends(get_current_user),
):
    """Get all client accounts managed by the agency."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.get_clients(
        agency_id=agency_id,
        status=status if status != "all" else None,
        search=search,
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": "Failed to load clients"},
        )
    
    # Transform clients to response format
    clients = [
        ClientSummary(
            clientID=str(c.get("client_id")),
            name=c.get("name"),
            adminEmail=c.get("admin_email"),
            status=c.get("status"),
            linkedinConnected=c.get("linkedin_connected", False),
            plan=c.get("plan"),
            lastActive=c.get("last_active"),
            createdAt=c.get("created_on"),
        )
        for c in result.data["clients"]
    ]
    
    return ClientListResponse(
        clients=clients,
        total=result.data["total"],
    )


@router.post(
    "/clients",
    response_model=CreateClientResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
    },
)
async def create_client(
    request: CreateClientRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Create a new client account under the agency."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.create_client(
        agency_id=agency_id,
        name=request.name,
        admin_email=request.admin_email,
        plan=request.plan,
    )
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return CreateClientResponse(
        clientID=result.data["clientID"],
        name=result.data["name"],
        adminEmail=result.data["adminEmail"],
        status=result.data["status"],
        linkedinConnected=result.data["linkedinConnected"],
        plan=result.data["plan"],
        createdAt=result.data["createdAt"],
        inviteLink=result.data.get("inviteLink"),
    )


@router.get(
    "/clients/{client_id}",
    response_model=ClientDetailResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def get_client(
    client_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Get detailed information about a specific client."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.get_client(agency_id, client_id)
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    data = result.data
    return ClientDetailResponse(
        clientID=data["clientID"],
        name=data["name"],
        adminEmail=data["adminEmail"],
        status=data["status"],
        linkedinConnected=data["linkedinConnected"],
        linkedinProfileUrl=data.get("linkedinProfileUrl"),
        plan=data["plan"],
        lastActive=data.get("lastActive"),
        createdAt=data["createdAt"],
        stats=ClientStats(
            totalCampaigns=data["stats"]["totalCampaigns"],
            totalProspects=data["stats"]["totalProspects"],
            meetingsBooked=data["stats"]["meetingsBooked"],
        ),
        team=[
            ClientTeamMember(
                teamMemberID=m["teamMemberID"],
                name=m.get("name"),
                email=m["email"],
                role=m["role"],
            )
            for m in data["team"]
        ],
    )


@router.patch(
    "/clients/{client_id}",
    response_model=ClientSummary,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def update_client(
    client_id: int,
    request: UpdateClientRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Update client account settings."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.update_client(
        agency_id=agency_id,
        client_id=client_id,
        name=request.name,
        plan=request.plan,
    )
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return ClientSummary(
        clientID=result.data["clientID"],
        name=result.data["name"],
        adminEmail=result.data["adminEmail"],
        status=result.data["status"],
        linkedinConnected=result.data["linkedinConnected"],
        plan=result.data["plan"],
        lastActive=result.data.get("lastActive"),
        createdAt=result.data["createdAt"],
    )


@router.delete(
    "/clients/{client_id}",
    response_model=SuccessResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def remove_client(
    client_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Remove a client account from the agency."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    
    result = await admin_service.remove_client(agency_id, client_id)
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return SuccessResponse(success=True, message=result.data["message"])


@router.post(
    "/clients/{client_id}/impersonate",
    response_model=ImpersonateResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
)
async def impersonate_client(
    client_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Generate a temporary token to log in as the client (for support purposes)."""
    context = await _require_admin(current_user)
    agency_id = context["agency_id"]
    member_id = context["member_id"]
    
    result = await admin_service.impersonate_client(
        agency_id=agency_id,
        member_id=member_id,
        client_id=client_id,
    )
    
    if not result.success:
        status_code = ERROR_STATUS_CODES.get(result.error, 500)
        raise HTTPException(
            status_code=status_code,
            detail={"error": result.error.value, "message": result.message},
        )
    
    return ImpersonateResponse(
        impersonationUrl=result.data["impersonationUrl"],
        expiresAt=result.data["expiresAt"],
    )

