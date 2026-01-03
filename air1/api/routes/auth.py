"""Auth API routes."""

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from air1.api.models.auth import AuthErrorResponse, LoginRequest, LoginResponse
from air1.services.user.service import Service

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Service instance
user_service = Service()


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": AuthErrorResponse, "description": "Invalid credentials"},
    },
)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    token = await user_service.authenticate(request.email, request.password)

    if not token:
        logger.warning(f"Failed login attempt for email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Invalid email or password"},
        )

    # Decode token to get user_id for response
    auth_user = user_service.verify_token(token)
    if not auth_user:
        logger.error(f"Failed to verify newly created token for email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_ERROR", "message": "Authentication failed"},
        )

    logger.info(f"Successful login for user_id: {auth_user.user_id}")
    return LoginResponse(
        auth_token=token,
        user_id=str(auth_user.user_id),
        email=auth_user.email,
    )

