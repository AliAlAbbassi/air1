"""Onboarding functions for user account creation."""
import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from air1.api.models.onboarding import (
    CompanyFetchResponse,
    OnboardingRequest,
    OnboardingResponse,
    UserResponse,
)
from air1.config import settings
from air1.services.outreach.onboarding_repo import (
    UserExistsError,
    create_user_with_onboarding,
    get_user_by_email,
)


class CreateUserInput(BaseModel):
    """Input model for creating a user with onboarding data."""

    email: str
    first_name: str
    last_name: str
    auth_method: str
    password_hash: Optional[str]
    timezone: str
    meeting_link: str
    linkedin_connected: bool
    company_name: str
    company_description: str
    company_website: str
    company_industry: str
    company_linkedin_url: str
    company_size: str
    product_name: str
    product_url: str
    product_description: str
    product_icp: str
    product_competitors: Optional[str]
    writing_style_template: Optional[str]
    writing_style_dos: list[str]
    writing_style_donts: list[str]


class EmailExistsError(Exception):
    """Raised when email already exists."""

    pass


class InvalidGoogleTokenError(Exception):
    """Raised when Google token is invalid."""

    pass


class InvalidLinkedInUrlError(Exception):
    """Raised when LinkedIn URL is invalid."""

    pass


def _hash_password(password: str) -> str:
    """Hash password using PBKDF2 with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"


def _create_jwt(user_id: int, email: str) -> str:
    """Create a JWT token."""
    jwt_secret = settings.jwt_secret
    jwt_expiry_hours = settings.jwt_expiry_hours

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": int(
            (datetime.now(timezone.utc) + timedelta(hours=jwt_expiry_hours)).timestamp()
        ),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }

    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    )

    signature = hmac.new(
        jwt_secret.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256,
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _validate_competitors_format(competitors: Optional[str]) -> Optional[str]:
    """
    Validate competitors field format (comma-separated list).
    Returns sanitized value or None if invalid format.
    """
    if not competitors:
        return None

    competitors = competitors.strip()
    if not competitors:
        return None

    parts = [p.strip() for p in competitors.split(",")]
    valid_parts = [p for p in parts if p and re.match(r"^[\w\s\-\.&]+$", p)]

    if not valid_parts:
        logger.warning(f"Invalid competitors format, ignoring: {competitors}")
        return None

    return ", ".join(valid_parts)


async def _verify_google_token(token: str) -> Optional[dict]:
    """Verify Google OAuth token."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}"
            )
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        logger.error(f"Failed to verify Google token: {e}")
        return None



async def create_onboarding_user(request: OnboardingRequest) -> OnboardingResponse:
    """Create a new user with all onboarding data."""
    auth = request.auth

    # Check if email exists
    existing_user = await get_user_by_email(auth.email)
    if existing_user:
        raise EmailExistsError("An account with this email already exists")

    # Verify Google token if using Google auth
    if auth.method.value == "google":
        google_info = await _verify_google_token(auth.google_access_token)
        if not google_info:
            raise InvalidGoogleTokenError("Invalid Google access token")

    # Hash password for email auth
    password_hash = None
    if auth.method.value == "email" and auth.password:
        password_hash = _hash_password(auth.password)

    # Validate and sanitize competitors format
    competitors = _validate_competitors_format(request.product.competitors)

    try:
        input_data = CreateUserInput(
            email=auth.email,
            first_name=auth.first_name,
            last_name=auth.last_name,
            auth_method=auth.method.value,
            password_hash=password_hash,
            timezone=request.profile.timezone,
            meeting_link=request.profile.meeting_link,
            linkedin_connected=request.linkedin.connected,
            company_name=request.company.name,
            company_description=request.company.description,
            company_website=request.company.website,
            company_industry=request.company.industry,
            company_linkedin_url=request.company.linkedin_url,
            company_size=request.company.employee_count.value,
            product_name=request.product.name,
            product_url=request.product.url,
            product_description=request.product.description,
            product_icp=request.product.ideal_customer_profile,
            product_competitors=competitors,
            writing_style_template=request.writing_style.selected_template,
            writing_style_dos=request.writing_style.dos,
            writing_style_donts=request.writing_style.donts,
        )
        success, user_id = await create_user_with_onboarding(input_data)

        if not success or not user_id:
            raise Exception("Failed to create user")

    except UserExistsError:
        raise EmailExistsError("An account with this email already exists")

    # Generate JWT token
    token = _create_jwt(user_id, auth.email)

    return OnboardingResponse(
        user=UserResponse(
            id=str(user_id),
            email=auth.email,
            firstName=auth.first_name,
            lastName=auth.last_name,
        ),
        token=token,
    )


async def fetch_company_from_linkedin(
    linkedin_url: str, browser_session
) -> CompanyFetchResponse:
    """
    Fetch company data from LinkedIn URL using browser scraper.

    Note: We use Playwright browser automation instead of httpx because:
    - LinkedIn requires authentication (li_at session cookie)
    - LinkedIn has bot detection that blocks raw HTTP requests
    """
    match = re.search(r"linkedin\.com/company/([^/?]+)", linkedin_url)
    if not match:
        raise InvalidLinkedInUrlError("Invalid LinkedIn company URL")

    company_username = match.group(1)

    company_data = await browser_session.get_company_info(company_username)
    return CompanyFetchResponse(
        name=company_data.get("name", ""),
        description=company_data.get("description", ""),
        website=company_data.get("website", ""),
        industry=company_data.get("industry", ""),
        logo=company_data.get("logo"),
    )
