"""Authentication utilities for API routes using Clerk."""

import os
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from loguru import logger

security = HTTPBearer()

# Initialize Clerk client
_clerk_secret = os.getenv("CLERK_SECRET_KEY")
_clerk = Clerk(bearer_auth=_clerk_secret) if _clerk_secret else None


@dataclass
class AuthUser:
    """Authenticated user from Clerk token."""

    user_id: str
    email: Optional[str] = None


def _starlette_to_httpx_request(request: Request) -> httpx.Request:
    """Convert FastAPI/Starlette request to httpx request for Clerk SDK."""
    return httpx.Request(
        method=request.method,
        url=str(request.url),
        headers=dict(request.headers),
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """Dependency to get the current authenticated user from Clerk token."""
    if not _clerk:
        logger.error("CLERK_SECRET_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CONFIG_ERROR", "message": "Authentication not configured"},
        )

    try:
        # Convert FastAPI request to httpx request for Clerk SDK
        httpx_request = _starlette_to_httpx_request(request)

        # Verify the token with Clerk (method on the SDK instance)
        request_state = _clerk.authenticate_request(
            httpx_request,
            AuthenticateRequestOptions(),
        )

        if not request_state.is_signed_in:
            logger.warning(f"Authentication failed: {request_state.reason}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "UNAUTHORIZED", "message": "Authentication required"},
            )

        # Extract user info from the token payload
        payload = request_state.payload
        user_id = payload.get("sub", "")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "UNAUTHORIZED", "message": "Invalid token payload"},
            )

        return AuthUser(user_id=user_id, email=email)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication failed"},
        )
