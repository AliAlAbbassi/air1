"""Account API routes."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from air1.api.auth import get_current_user
from air1.services.user.service import AuthUser
from air1.api.models.account import (
    AccountResponse,
    AccountUpdateRequest,
    CompanyData,
    ErrorResponse,
    LinkedinData,
    UserData,
)
from air1.services.user.service import Service

router = APIRouter(prefix="/api/account", tags=["account"])

# Service instance
user_service = Service()

# Default daily limits
DEFAULT_CONNECTION_LIMIT = 25
DEFAULT_INMAIL_LIMIT = 40


def _build_account_response(account_data: dict) -> AccountResponse:
    """Build AccountResponse from database row."""
    user_id = str(account_data["user_id"])
    company_id = account_data.get("company_id")
    linkedin_username = account_data.get("company_linkedin_username")

    return AccountResponse(
        user=UserData(
            id=user_id,
            email=account_data["email"],
            firstName=account_data["first_name"] or "",
            lastName=account_data["last_name"] or "",
            avatarUrl=None,
            timezone=account_data["timezone"] or "UTC",
            meetingLink=account_data["meeting_link"] or "",
        ),
        linkedin=LinkedinData(
            connected=account_data.get("linkedin_connected", False),
            profileUrl=f"https://linkedin.com/in/{linkedin_username}" if linkedin_username else None,
            dailyLimits={
                "connections": DEFAULT_CONNECTION_LIMIT,
                "inmails": DEFAULT_INMAIL_LIMIT,
            },
        ),
        company=CompanyData(
            id=str(company_id) if company_id else "",
            name=account_data.get("company_name") or "",
            logo=None,
            plan="free",  # Default plan
        ),
    )


@router.get(
    "",
    response_model=AccountResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_account(current_user: AuthUser = Depends(get_current_user)):
    """Get the authenticated user's account data."""
    account_data = await user_service.get_account(current_user.user_id)

    if not account_data:
        logger.error(f"Account not found for user_id: {current_user.user_id}")
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Account not found"},
        )

    return _build_account_response(account_data)


@router.patch(
    "",
    response_model=AccountResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def update_account(
    request: AccountUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Update the authenticated user's profile settings."""
    # Check if any field is provided
    update_fields = request.model_dump(exclude_unset=True, by_alias=False)
    if not update_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "VALIDATION_ERROR",
                "message": "Invalid request body",
                "details": [{"field": "body", "message": "At least one field is required"}],
            },
        )

    success = await user_service.update_profile(
        user_id=current_user.user_id,
        first_name=request.first_name,
        last_name=request.last_name,
        timezone=request.timezone,
        meeting_link=request.meeting_link,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": "Failed to update profile"},
        )

    # Fetch and return updated account
    account_data = await user_service.get_account(current_user.user_id)
    if not account_data:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Account not found"},
        )

    return _build_account_response(account_data)
