"""Pydantic models for Admin API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
import re


# ============================================================================
# COMMON
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str


# ============================================================================
# TEAM MANAGEMENT
# ============================================================================


class TeamMember(BaseModel):
    """Team member data."""

    member_id: str = Field(..., alias="memberID")
    name: Optional[str] = None
    email: str
    role: str  # owner | admin | manager
    status: str  # active | pending
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    invited_at: datetime = Field(..., alias="invitedAt")
    joined_at: Optional[datetime] = Field(None, alias="joinedAt")

    model_config = {"populate_by_name": True, "by_alias": True}


class TeamListResponse(BaseModel):
    """GET /api/admin/team response."""

    members: list[TeamMember]
    total_seats: int = Field(..., alias="totalSeats")
    used_seats: int = Field(..., alias="usedSeats")

    model_config = {"populate_by_name": True, "by_alias": True}


class InviteTeamMemberRequest(BaseModel):
    """POST /api/admin/team/invite request body."""

    email: str
    role: str  # admin | manager

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["admin", "manager"]:
            raise ValueError("Role must be 'admin' or 'manager'")
        return v


class InviteTeamMemberResponse(BaseModel):
    """POST /api/admin/team/invite response."""

    member_id: str = Field(..., alias="memberID")
    email: str
    role: str
    status: str
    invited_at: datetime = Field(..., alias="invitedAt")

    model_config = {"populate_by_name": True, "by_alias": True}


class UpdateMemberRoleRequest(BaseModel):
    """PATCH /api/admin/team/:memberId/role request body."""

    role: str  # admin | manager

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["admin", "manager"]:
            raise ValueError("Role must be 'admin' or 'manager'")
        return v


class UpdateMemberRoleResponse(BaseModel):
    """PATCH /api/admin/team/:memberId/role response."""

    member_id: str = Field(..., alias="memberID")
    role: str
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {"populate_by_name": True, "by_alias": True}


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str


# ============================================================================
# CLIENT MANAGEMENT
# ============================================================================


class ClientSummary(BaseModel):
    """Client summary for list responses."""

    client_id: str = Field(..., alias="clientID")
    name: str
    admin_email: str = Field(..., alias="adminEmail")
    status: str  # active | onboarding
    linkedin_connected: bool = Field(..., alias="linkedinConnected")
    plan: str  # starter | pro | enterprise
    last_active: Optional[datetime] = Field(None, alias="lastActive")
    created_at: datetime = Field(..., alias="createdAt")

    model_config = {"populate_by_name": True, "by_alias": True}


class ClientListResponse(BaseModel):
    """GET /api/admin/clients response."""

    clients: list[ClientSummary]
    total: int

    model_config = {"populate_by_name": True, "by_alias": True}


class CreateClientRequest(BaseModel):
    """POST /api/admin/clients request body."""

    name: str
    admin_email: str = Field(..., alias="adminEmail")
    plan: str  # starter | pro | enterprise

    model_config = {"populate_by_name": True}

    @field_validator("admin_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in ["starter", "pro", "enterprise"]:
            raise ValueError("Plan must be 'starter', 'pro', or 'enterprise'")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v.strip()) < 2:
            raise ValueError("Name is required and must be at least 2 characters")
        return v.strip()


class CreateClientResponse(BaseModel):
    """POST /api/admin/clients response."""

    client_id: str = Field(..., alias="clientID")
    name: str
    admin_email: str = Field(..., alias="adminEmail")
    status: str
    linkedin_connected: bool = Field(..., alias="linkedinConnected")
    plan: str
    created_at: datetime = Field(..., alias="createdAt")
    invite_link: Optional[str] = Field(None, alias="inviteLink")

    model_config = {"populate_by_name": True, "by_alias": True}


class ClientStats(BaseModel):
    """Client statistics."""

    total_campaigns: int = Field(..., alias="totalCampaigns")
    total_prospects: int = Field(..., alias="totalProspects")
    meetings_booked: int = Field(..., alias="meetingsBooked")

    model_config = {"populate_by_name": True, "by_alias": True}


class ClientTeamMember(BaseModel):
    """Client team member."""

    team_member_id: str = Field(..., alias="teamMemberID")
    name: Optional[str] = None
    email: str
    role: str

    model_config = {"populate_by_name": True, "by_alias": True}


class ClientDetailResponse(BaseModel):
    """GET /api/admin/clients/:clientId response."""

    client_id: str = Field(..., alias="clientID")
    name: str
    admin_email: str = Field(..., alias="adminEmail")
    status: str
    linkedin_connected: bool = Field(..., alias="linkedinConnected")
    linkedin_profile_url: Optional[str] = Field(None, alias="linkedinProfileUrl")
    plan: str
    last_active: Optional[datetime] = Field(None, alias="lastActive")
    created_at: datetime = Field(..., alias="createdAt")
    stats: ClientStats
    team: list[ClientTeamMember]

    model_config = {"populate_by_name": True, "by_alias": True}


class UpdateClientRequest(BaseModel):
    """PATCH /api/admin/clients/:clientId request body."""

    name: Optional[str] = None
    plan: Optional[str] = None  # starter | pro | enterprise

    model_config = {"populate_by_name": True}

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["starter", "pro", "enterprise"]:
            raise ValueError("Plan must be 'starter', 'pro', or 'enterprise'")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip() if v else v


class ImpersonateResponse(BaseModel):
    """POST /api/admin/clients/:clientId/impersonate response."""

    impersonation_url: str = Field(..., alias="impersonationUrl")
    expires_at: datetime = Field(..., alias="expiresAt")

    model_config = {"populate_by_name": True, "by_alias": True}

