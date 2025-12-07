"""Unit tests for onboarding functionality."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from air1.services.outreach.onboarding import (
    CreateUserInput,
    EmailExistsError,
    InvalidGoogleTokenError,
    InvalidLinkedInUrlError,
    _hash_password,
    _create_jwt,
    _validate_competitors_format,
    _verify_google_token,
    create_onboarding_user,
    fetch_company_from_linkedin,
)
from air1.api.models.onboarding import (
    OnboardingRequest,
    AuthData,
    AuthMethod,
    CompanyData,
    EmployeeCount,
    ProductData,
    WritingStyleData,
    LinkedinData,
    ProfileData,
)


# ============================================================================
# Test CreateUserInput Model
# ============================================================================


class TestCreateUserInput:
    def test_create_user_input_valid(self):
        """Test creating a valid CreateUserInput model."""
        data = CreateUserInput(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            auth_method="email",
            password_hash="salt:hash",
            timezone="EST",
            meeting_link="https://cal.com/john",
            linkedin_connected=True,
            company_name="Acme Inc",
            company_description="We build things",
            company_website="https://acme.com",
            company_industry="Technology",
            company_linkedin_url="https://linkedin.com/company/acme",
            company_size="10-100",
            product_name="Acme SDK",
            product_url="https://acme.com/sdk",
            product_description="Developer SDK",
            product_icp="Engineering leaders",
            product_competitors="Stripe, Twilio",
            writing_style_template="engineering-leader",
            writing_style_dos=["be technical"],
            writing_style_donts=["use buzzwords"],
        )
        assert data.email == "test@example.com"
        assert data.first_name == "John"

    def test_create_user_input_optional_fields(self):
        """Test CreateUserInput with optional fields as None."""
        data = CreateUserInput(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            auth_method="google",
            password_hash=None,
            timezone="EST",
            meeting_link="https://cal.com/john",
            linkedin_connected=False,
            company_name="Acme Inc",
            company_description="We build things",
            company_website="https://acme.com",
            company_industry="Technology",
            company_linkedin_url="https://linkedin.com/company/acme",
            company_size="10-100",
            product_name="Acme SDK",
            product_url="https://acme.com/sdk",
            product_description="Developer SDK",
            product_icp="Engineering leaders",
            product_competitors=None,
            writing_style_template=None,
            writing_style_dos=[],
            writing_style_donts=[],
        )
        assert data.password_hash is None
        assert data.product_competitors is None


# ============================================================================
# Test Password Hashing
# ============================================================================


class TestPasswordHashing:
    def test_hash_password_returns_salt_and_hash(self):
        """Test that password hashing returns salt:hash format."""
        result = _hash_password("mypassword123")
        assert ":" in result
        parts = result.split(":")
        assert len(parts) == 2
        assert len(parts[0]) == 32  # salt is 16 bytes hex = 32 chars
        assert len(parts[1]) == 64  # sha256 hash is 32 bytes hex = 64 chars

    def test_hash_password_different_salts(self):
        """Test that same password produces different hashes (different salts)."""
        hash1 = _hash_password("mypassword123")
        hash2 = _hash_password("mypassword123")
        assert hash1 != hash2  # Different salts should produce different results


# ============================================================================
# Test JWT Creation
# ============================================================================


class TestJWTCreation:
    @patch("air1.services.outreach.onboarding.settings")
    def test_create_jwt_returns_valid_format(self, mock_settings):
        """Test that JWT creation returns valid format."""
        mock_settings.jwt_secret = "test-secret"
        mock_settings.jwt_expiry_hours = 24

        token = _create_jwt(123, "test@example.com")

        assert token is not None
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    @patch("air1.services.outreach.onboarding.settings")
    def test_create_jwt_different_users_different_tokens(self, mock_settings):
        """Test that different users get different tokens."""
        mock_settings.jwt_secret = "test-secret"
        mock_settings.jwt_expiry_hours = 24

        token1 = _create_jwt(123, "user1@example.com")
        token2 = _create_jwt(456, "user2@example.com")

        assert token1 != token2



# ============================================================================
# Test Competitors Validation
# ============================================================================


class TestCompetitorsValidation:
    def test_validate_competitors_valid_format(self):
        """Test valid comma-separated competitors."""
        result = _validate_competitors_format("Stripe, Twilio, Plaid")
        assert result == "Stripe, Twilio, Plaid"

    def test_validate_competitors_with_extra_spaces(self):
        """Test competitors with extra spaces are normalized."""
        result = _validate_competitors_format("  Stripe  ,  Twilio  ,  Plaid  ")
        assert result == "Stripe, Twilio, Plaid"

    def test_validate_competitors_with_special_chars(self):
        """Test competitors with allowed special characters."""
        result = _validate_competitors_format("AT&T, Johnson & Johnson, 3M")
        assert result == "AT&T, Johnson & Johnson, 3M"

    def test_validate_competitors_empty_string(self):
        """Test empty string returns None."""
        result = _validate_competitors_format("")
        assert result is None

    def test_validate_competitors_none(self):
        """Test None input returns None."""
        result = _validate_competitors_format(None)
        assert result is None

    def test_validate_competitors_whitespace_only(self):
        """Test whitespace-only string returns None."""
        result = _validate_competitors_format("   ")
        assert result is None

    def test_validate_competitors_invalid_chars_filtered(self):
        """Test that invalid characters are filtered out."""
        result = _validate_competitors_format("Valid, <script>alert('xss')</script>")
        assert result == "Valid"

    def test_validate_competitors_all_invalid_returns_none(self):
        """Test that all invalid entries returns None."""
        result = _validate_competitors_format("<script>, @#$%")
        assert result is None


# ============================================================================
# Test Google Token Verification
# ============================================================================


class TestGoogleTokenVerification:
    @pytest.mark.asyncio
    async def test_verify_google_token_success(self):
        """Test successful Google token verification."""
        with patch("air1.services.outreach.onboarding.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"email": "test@gmail.com"}

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await _verify_google_token("valid_token")

            assert result is not None
            assert result["email"] == "test@gmail.com"

    @pytest.mark.asyncio
    async def test_verify_google_token_invalid(self):
        """Test invalid Google token returns None."""
        with patch("air1.services.outreach.onboarding.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await _verify_google_token("invalid_token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_google_token_network_error(self):
        """Test network error returns None."""
        with patch("air1.services.outreach.onboarding.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = Exception("Network error")
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await _verify_google_token("some_token")

            assert result is None


# ============================================================================
# Test Create Onboarding User
# ============================================================================


def _create_mock_request(auth_method="email", password="password123"):
    """Helper to create a mock OnboardingRequest."""
    auth_data = {
        "method": auth_method,
        "email": "test@example.com",
        "firstName": "John",
        "lastName": "Doe",
    }
    if auth_method == "email":
        auth_data["password"] = password
    else:
        auth_data["googleAccessToken"] = "valid_google_token"

    return OnboardingRequest(
        auth=AuthData(**auth_data),
        company=CompanyData(
            name="Acme Inc",
            description="We build things",
            website="https://acme.com",
            industry="Technology",
            linkedinUrl="https://linkedin.com/company/acme",
            employeeCount=EmployeeCount.SMALL,
        ),
        product=ProductData(
            name="Acme SDK",
            url="https://acme.com/sdk",
            description="Developer SDK",
            idealCustomerProfile="Engineering leaders",
            competitors="Stripe, Twilio",
        ),
        writingStyle=WritingStyleData(
            selectedTemplate="engineering-leader",
            dos=["be technical"],
            donts=["use buzzwords"],
        ),
        linkedin=LinkedinData(connected=True),
        profile=ProfileData(
            timezone="EST",
            meetingLink="https://cal.com/john",
        ),
    )


class TestCreateOnboardingUser:
    @pytest.mark.asyncio
    async def test_create_user_email_auth_success(self):
        """Test successful user creation with email auth."""
        request = _create_mock_request(auth_method="email")

        with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
             patch("air1.services.outreach.onboarding.create_user_with_onboarding") as mock_create, \
             patch("air1.services.outreach.onboarding.settings") as mock_settings:

            mock_get_user.return_value = None  # User doesn't exist
            mock_create.return_value = (True, 123)
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_expiry_hours = 24

            result = await create_onboarding_user(request)

            assert result is not None
            assert result.user.id == "123"
            assert result.user.email == "test@example.com"
            assert result.token is not None

    @pytest.mark.asyncio
    async def test_create_user_email_exists_error(self):
        """Test that existing email raises EmailExistsError."""
        request = _create_mock_request(auth_method="email")

        with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user:
            mock_get_user.return_value = {"user_id": 1, "email": "test@example.com"}

            with pytest.raises(EmailExistsError):
                await create_onboarding_user(request)

    @pytest.mark.asyncio
    async def test_create_user_google_auth_success(self):
        """Test successful user creation with Google auth."""
        request = _create_mock_request(auth_method="google")

        with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
             patch("air1.services.outreach.onboarding.create_user_with_onboarding") as mock_create, \
             patch("air1.services.outreach.onboarding._verify_google_token") as mock_verify, \
             patch("air1.services.outreach.onboarding.settings") as mock_settings:

            mock_get_user.return_value = None
            mock_verify.return_value = {"email": "test@gmail.com"}
            mock_create.return_value = (True, 456)
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_expiry_hours = 24

            result = await create_onboarding_user(request)

            assert result is not None
            assert result.user.id == "456"

    @pytest.mark.asyncio
    async def test_create_user_invalid_google_token(self):
        """Test that invalid Google token raises InvalidGoogleTokenError."""
        request = _create_mock_request(auth_method="google")

        with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
             patch("air1.services.outreach.onboarding._verify_google_token") as mock_verify:

            mock_get_user.return_value = None
            mock_verify.return_value = None  # Invalid token

            with pytest.raises(InvalidGoogleTokenError):
                await create_onboarding_user(request)



# ============================================================================
# Test Fetch Company From LinkedIn
# ============================================================================


class TestFetchCompanyFromLinkedIn:
    @pytest.mark.asyncio
    async def test_fetch_company_valid_url(self):
        """Test fetching company data with valid LinkedIn URL."""
        mock_session = AsyncMock()
        mock_session.get_company_info.return_value = {
            "name": "Acme Inc",
            "description": "We build things",
            "website": "https://acme.com",
            "industry": "Technology",
            "logo": "https://acme.com/logo.png",
        }

        result = await fetch_company_from_linkedin(
            "https://linkedin.com/company/acme",
            mock_session,
        )

        assert result.name == "Acme Inc"
        assert result.description == "We build things"
        assert result.website == "https://acme.com"
        assert result.industry == "Technology"
        assert result.logo == "https://acme.com/logo.png"

    @pytest.mark.asyncio
    async def test_fetch_company_invalid_url(self):
        """Test that invalid LinkedIn URL raises InvalidLinkedInUrlError."""
        mock_session = AsyncMock()

        with pytest.raises(InvalidLinkedInUrlError):
            await fetch_company_from_linkedin(
                "https://example.com/not-linkedin",
                mock_session,
            )

    @pytest.mark.asyncio
    async def test_fetch_company_url_with_query_params(self):
        """Test fetching company with URL containing query params."""
        mock_session = AsyncMock()
        mock_session.get_company_info.return_value = {
            "name": "Test Corp",
            "description": "Testing",
            "website": "https://test.com",
            "industry": "Tech",
        }

        result = await fetch_company_from_linkedin(
            "https://www.linkedin.com/company/testcorp?trk=some_tracking",
            mock_session,
        )

        assert result.name == "Test Corp"
        mock_session.get_company_info.assert_called_once_with("testcorp")

    @pytest.mark.asyncio
    async def test_fetch_company_missing_optional_fields(self):
        """Test fetching company when some fields are missing."""
        mock_session = AsyncMock()
        mock_session.get_company_info.return_value = {
            "name": "Minimal Corp",
            "description": "",
            "website": "",
            "industry": "",
        }

        result = await fetch_company_from_linkedin(
            "https://linkedin.com/company/minimal",
            mock_session,
        )

        assert result.name == "Minimal Corp"
        assert result.description == ""
        assert result.logo is None


# ============================================================================
# Test Onboarding Repo Functions
# ============================================================================


class TestOnboardingRepo:
    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self):
        """Test getting user by email when user exists."""
        from air1.services.outreach.onboarding_repo import get_user_by_email

        with patch("air1.services.outreach.onboarding_repo.get_prisma") as mock_get_prisma, \
             patch("air1.services.outreach.onboarding_repo.queries") as mock_queries:

            mock_prisma = AsyncMock()
            mock_get_prisma.return_value = mock_prisma
            mock_queries.get_user_by_email = AsyncMock(
                return_value={"user_id": 1, "email": "test@example.com"}
            )

            result = await get_user_by_email("test@example.com")

            assert result is not None
            assert result["user_id"] == 1

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        """Test getting user by email when user doesn't exist."""
        from air1.services.outreach.onboarding_repo import get_user_by_email

        with patch("air1.services.outreach.onboarding_repo.get_prisma") as mock_get_prisma, \
             patch("air1.services.outreach.onboarding_repo.queries") as mock_queries:

            mock_prisma = AsyncMock()
            mock_get_prisma.return_value = mock_prisma
            mock_queries.get_user_by_email = AsyncMock(return_value=None)

            result = await get_user_by_email("nonexistent@example.com")

            assert result is None

    @pytest.mark.asyncio
    async def test_create_user_with_onboarding_success(self):
        """Test successful user creation with all onboarding data."""
        from air1.services.outreach.onboarding_repo import create_user_with_onboarding

        input_data = CreateUserInput(
            email="new@example.com",
            first_name="New",
            last_name="User",
            auth_method="email",
            password_hash="salt:hash",
            timezone="EST",
            meeting_link="https://cal.com/new",
            linkedin_connected=False,
            company_name="New Corp",
            company_description="New company",
            company_website="https://new.com",
            company_industry="Tech",
            company_linkedin_url="https://linkedin.com/company/new",
            company_size="0-10",
            product_name="New Product",
            product_url="https://new.com/product",
            product_description="New product desc",
            product_icp="Startups",
            product_competitors=None,
            writing_style_template=None,
            writing_style_dos=[],
            writing_style_donts=[],
        )

        with patch("air1.services.outreach.onboarding_repo.get_prisma") as mock_get_prisma, \
             patch("air1.services.outreach.onboarding_repo.queries") as mock_queries:

            # Create proper async context manager mock for transaction
            mock_tx = MagicMock()
            mock_tx_cm = MagicMock()
            mock_tx_cm.__aenter__ = AsyncMock(return_value=mock_tx)
            mock_tx_cm.__aexit__ = AsyncMock(return_value=None)

            mock_prisma = MagicMock()
            mock_prisma.tx.return_value = mock_tx_cm
            # get_prisma is async, so return_value needs to be awaitable
            mock_get_prisma.return_value = mock_prisma

            mock_queries.insert_user = AsyncMock(return_value={"userId": 999})
            mock_queries.insert_user_company = AsyncMock(return_value={"companyId": 1})
            mock_queries.insert_user_product = AsyncMock(return_value={"productId": 1})
            mock_queries.insert_user_writing_style = AsyncMock(return_value={"writingStyleId": 1})

            success, user_id = await create_user_with_onboarding(input_data)

            assert success is True
            assert user_id == 999

    @pytest.mark.asyncio
    async def test_create_user_with_onboarding_duplicate_email(self):
        """Test that duplicate email raises UserExistsError."""
        from air1.services.outreach.onboarding_repo import (
            create_user_with_onboarding,
            UserExistsError,
        )

        input_data = CreateUserInput(
            email="existing@example.com",
            first_name="Existing",
            last_name="User",
            auth_method="email",
            password_hash="salt:hash",
            timezone="EST",
            meeting_link="https://cal.com/existing",
            linkedin_connected=False,
            company_name="Existing Corp",
            company_description="Existing company",
            company_website="https://existing.com",
            company_industry="Tech",
            company_linkedin_url="https://linkedin.com/company/existing",
            company_size="0-10",
            product_name="Existing Product",
            product_url="https://existing.com/product",
            product_description="Existing product desc",
            product_icp="Enterprises",
            product_competitors=None,
            writing_style_template=None,
            writing_style_dos=[],
            writing_style_donts=[],
        )

        with patch("air1.services.outreach.onboarding_repo.get_prisma") as mock_get_prisma, \
             patch("air1.services.outreach.onboarding_repo.queries") as mock_queries:

            # Create proper async context manager mock for transaction
            mock_tx = MagicMock()
            mock_tx_cm = MagicMock()
            mock_tx_cm.__aenter__ = AsyncMock(return_value=mock_tx)
            mock_tx_cm.__aexit__ = AsyncMock(return_value=None)

            mock_prisma = MagicMock()
            mock_prisma.tx.return_value = mock_tx_cm
            mock_get_prisma.return_value = mock_prisma

            # ON CONFLICT DO NOTHING returns None
            mock_queries.insert_user = AsyncMock(return_value=None)

            with pytest.raises(UserExistsError):
                await create_user_with_onboarding(input_data)
