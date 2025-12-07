from fastapi import APIRouter, HTTPException
from loguru import logger

from air1.api.models.onboarding import (
    OnboardingRequest,
    OnboardingResponse,
    CompanyFetchRequest,
    CompanyFetchResponse,
    ErrorResponse,
)
from air1.services.outreach.onboarding import (
    EmailExistsError,
    InvalidGoogleTokenError,
    InvalidLinkedInUrlError,
)
from air1.services.outreach.service import Service

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post(
    "",
    response_model=OnboardingResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
)
async def create_account(request: OnboardingRequest):
    """
    Create a new user account with all onboarding data.

    This endpoint handles both email and Google authentication methods.
    """
    async with Service() as service:
        try:
            return await service.create_onboarding_user(request)
        except EmailExistsError:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "EMAIL_EXISTS",
                    "message": "An account with this email already exists",
                },
            )
        except InvalidGoogleTokenError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_GOOGLE_TOKEN",
                    "message": "Invalid Google access token",
                },
            )
        except Exception as e:
            logger.error(f"Onboarding error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                },
            )


@router.post(
    "/company/fetch",
    response_model=CompanyFetchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        404: {"model": ErrorResponse, "description": "Company not found"},
    },
)
async def fetch_company(request: CompanyFetchRequest):
    """
    Fetch company data from a LinkedIn company URL using AI scraping.
    """
    async with Service() as service:
        try:
            return await service.fetch_company_from_linkedin(request.linkedin_url)
        except InvalidLinkedInUrlError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_URL",
                    "message": "Invalid LinkedIn company URL",
                },
            )
        except Exception as e:
            logger.error(f"Company fetch error: {e}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "COMPANY_NOT_FOUND",
                    "message": "Could not find company data for this URL",
                },
            )
