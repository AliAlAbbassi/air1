import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import base64
import hmac

from loguru import logger
from prisma import Prisma

from air1.api.models.onboarding import (
    OnboardingRequest,
    OnboardingResponse,
    UserResponse,
    CompanyFetchResponse,
)
from air1.config import settings


class OnboardingService:
    def __init__(self, db: Prisma):
        self.db = db
        self._jwt_secret = getattr(settings, "jwt_secret", "dev-secret-change-in-production")
        self._jwt_expiry_hours = getattr(settings, "jwt_expiry_hours", 24 * 7)

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}:{hashed.hex()}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        salt, hash_hex = stored_hash.split(":")
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hashed.hex() == hash_hex

    def _create_jwt(self, user_id: int, email: str) -> str:
        """Create a simple JWT token."""
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


    async def check_email_exists(self, email: str) -> bool:
        """Check if email already exists in database."""
        user = await self.db.hodhoduser.find_unique(where={"email": email})
        return user is not None

    async def verify_google_token(self, token: str) -> Optional[dict]:
        """Verify Google OAuth token. Returns user info if valid."""
        # In production, call Google's tokeninfo endpoint
        # For now, we'll trust the token and extract info from it
        # TODO: Implement actual Google token verification
        import httpx
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
        if await self.check_email_exists(auth.email):
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

        # Create user in transaction
        async with self.db.tx() as tx:
            # Create user
            user = await tx.hodhoduser.create(
                data={
                    "email": auth.email,
                    "firstName": auth.first_name,
                    "lastName": auth.last_name,
                    "passwordHash": password_hash,
                    "authMethod": auth.method.value,
                    "fullName": request.profile.full_name,
                    "timezone": request.profile.timezone,
                    "meetingLink": request.profile.meeting_link,
                    "linkedinConnected": request.linkedin.connected,
                }
            )

            # Create company
            company = await tx.hodhodcompany.create(
                data={
                    "userId": user.id,
                    "name": request.company.name,
                    "description": request.company.description,
                    "website": request.company.website,
                    "industry": request.company.industry,
                    "linkedinUrl": request.company.linkedin_url,
                    "employeeCount": request.company.employee_count.value,
                }
            )

            # Create product
            await tx.hodhodproduct.create(
                data={
                    "userId": user.id,
                    "companyId": company.id,
                    "name": request.product.name,
                    "url": request.product.url,
                    "description": request.product.description,
                    "idealCustomerProfile": request.product.ideal_customer_profile,
                    "competitors": request.product.competitors,
                }
            )

            # Create writing style
            await tx.hodhodwritingstyle.create(
                data={
                    "userId": user.id,
                    "selectedTemplate": request.writing_style.selected_template,
                    "dos": request.writing_style.dos,
                    "donts": request.writing_style.donts,
                }
            )

        # Generate JWT token
        token = self._create_jwt(user.id, user.email)

        return OnboardingResponse(
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                firstName=user.firstName,
                lastName=user.lastName,
            ),
            token=token,
        )

    async def fetch_company_data(self, linkedin_url: str) -> CompanyFetchResponse:
        """Fetch company data from LinkedIn URL using scraper."""
        # Extract company username from URL
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


class EmailExistsError(Exception):
    """Raised when email already exists."""
    pass


class InvalidGoogleTokenError(Exception):
    """Raised when Google token is invalid."""
    pass


class InvalidLinkedInUrlError(Exception):
    """Raised when LinkedIn URL is invalid."""
    pass
