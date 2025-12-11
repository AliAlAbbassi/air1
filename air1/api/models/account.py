"""Pydantic models for Account API."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class UserData(BaseModel):
    """User profile data."""

    id: str
    email: str
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    timezone: str
    meeting_link: str = Field(..., alias="meetingLink")

    model_config = {"populate_by_name": True, "by_alias": True}


class LinkedinData(BaseModel):
    """LinkedIn connection data."""

    connected: bool
    profile_url: Optional[str] = Field(None, alias="profileUrl")
    daily_limits: dict = Field(..., alias="dailyLimits")

    model_config = {"populate_by_name": True, "by_alias": True}


class CompanyData(BaseModel):
    """Company data."""

    id: str
    name: str
    logo: Optional[str] = None
    plan: str  # free | pro | enterprise

    model_config = {"populate_by_name": True, "by_alias": True}


class AccountResponse(BaseModel):
    """GET /api/account response."""

    user: UserData
    linkedin: LinkedinData
    company: CompanyData


class AccountUpdateRequest(BaseModel):
    """PATCH /api/account request body."""

    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    timezone: Optional[str] = None
    meeting_link: Optional[str] = Field(None, alias="meetingLink")

    model_config = {"populate_by_name": True}

    @field_validator("meeting_link")
    @classmethod
    def validate_meeting_link(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^https?://", v):
            raise ValueError("Invalid URL format")
        return v


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
    details: Optional[list[ValidationErrorDetail]] = None
