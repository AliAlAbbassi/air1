"""Onboarding service for user account creation."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import json
import base64
import hmac
from typing import Optional

from loguru import logger
import httpx

from air1.api.models.onboarding import (
    OnboardingRequest,
    OnboardingResponse,
    UserResponse,
    CompanyFetchResponse,
)
from air1.services.outreach.onboarding_repo import (
    get_user_by_email,
    create_user_with_onboarding,
    UserExistsError,
)
from air1.config import settings


class EmailExistsError(Exception):
    """Raised when email already exists."""
    pass


class InvalidGoogleTokenError(Exception):
    """Raised when Google token is invalid."""
    pass


class InvalidLinkedInUrlError(Exception):
    """Raised when LinkedIn URL is invalid."""
    pass


class OnboardingService:
    def __init__(self):
        self._jwt_secret = settings.jwt_secret
        self._jwt_expiry_hours = settings.jwt_expiry_hours

    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2 with salt."""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}:{hashed.hex()}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        salt, hash_hex = stored_hash.split(":")
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hashed.hex() == hash_hex

    def _create_jwt(self, user_id: int, email: str) -> str:
        """Create a JWT token."""
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=self._jwt_expiry_hours)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        
        signature = hmac.new(
            self._jwt_secret.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    async def verify_google_token(self, token: str) -> Optional[dict]:
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


    async def create_user(self, request: OnboardingRequest) -> OnboardingResponse:
        """Create a new user with all onboarding data."""
        auth = request.auth
        
        # Check if email exists
        existing_user = await get_user_by_email(auth.email)
        if existing_user:
            raise EmailExistsError("An account with this email already exists")

        # Verify Google token if using Google auth
        if auth.method.value == "google":
            google_info = await self.verify_google_token(auth.google_access_token)
            if not google_info:
                raise InvalidGoogleTokenError("Invalid Google access token")

        # Hash password for email auth
        password_hash = None
        if auth.method.value == "email" and auth.password:
            password_hash = self._hash_password(auth.password)

        try:
            success, user_id = await create_user_with_onboarding(
                email=auth.email,
                first_name=auth.first_name,
                last_name=auth.last_name,
                full_name=request.profile.full_name,
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
                product_competitors=request.product.competitors,
                writing_style_template=request.writing_style.selected_template,
                writing_style_dos=request.writing_style.dos,
                writing_style_donts=request.writing_style.donts,
            )
            
            if not success or not user_id:
                raise Exception("Failed to create user")
                
        except UserExistsError:
            raise EmailExistsError("An account with this email already exists")

        # Generate JWT token
        token = self._create_jwt(user_id, auth.email)

        return OnboardingResponse(
            user=UserResponse(
                id=str(user_id),
                email=auth.email,
                firstName=auth.first_name,
                lastName=auth.last_name,
            ),
            token=token,
        )

    async def fetch_company_data(self, linkedin_url: str) -> CompanyFetchResponse:
        """Fetch company data from LinkedIn URL using scraper."""
        import re
        match = re.search(r"linkedin\.com/company/([^/?]+)", linkedin_url)
        if not match:
            raise InvalidLinkedInUrlError("Invalid LinkedIn company URL")
        
        company_username = match.group(1)
        
        # Use existing scraper infrastructure
        from air1.services.outreach.service import Service
        
        async with Service() as service:
            session = await service.launch_browser(headless=True)
            try:
                company_data = await session.get_company_info(company_username)
                return CompanyFetchResponse(
                    name=company_data.get("name", ""),
                    description=company_data.get("description", ""),
                    website=company_data.get("website", ""),
                    industry=company_data.get("industry", ""),
                    logo=company_data.get("logo"),
                )
            finally:
                await session.browser.close()
