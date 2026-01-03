"""Pydantic models for Auth API."""

from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """POST /api/auth/login request body."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """POST /api/auth/login response."""

    auth_token: str = Field(..., alias="authToken")
    user_id: str = Field(..., alias="userId")
    email: str

    model_config = {"populate_by_name": True, "by_alias": True}


class AuthErrorResponse(BaseModel):
    """Authentication error response."""

    error: str
    message: str

