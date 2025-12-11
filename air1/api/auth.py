"""Authentication utilities for API routes."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from air1.services.user.service import AuthUser, UserService

security = HTTPBearer()

# Service instance for token verification
_user_service = UserService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """Dependency to get the current authenticated user from JWT token."""
    token = credentials.credentials
    auth_user = _user_service.verify_token(token)

    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required"},
        )

    return auth_user
