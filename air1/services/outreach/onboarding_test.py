"""Tests for onboarding functionality.

Run with mocks (default):
    pytest air1/services/outreach/onboarding_test.py -v

Run against real database:
    pytest air1/services/outreach/onboarding_test.py --use-real-db -v
"""
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

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
# Test Fixtures
# ============================================================================


@pytest.fixture
def test_email():
    """Generate unique test email for each test."""
    test_uuid = str(uuid.uuid4())[:8]
    return f"test.{test_uuid}@example.com"


@pytest.fixture
def test_uuid():
    """Generate unique UUID for test data."""
    return str(uuid.uuid4())[:8]


# ============================================================================
# Mock Helpers
# ============================================================================


@asynccontextmanager
async def mock_db_context():
    """Context manager for mocking database operations."""
    with patch("air1.services.outreach.onboarding_repo.get_prisma") as mock_get_prisma, \
         patch("air1.services.outreach.onboarding_repo.queries") as mock_queries:
        
        mock_tx = MagicMock()
        mock_tx_cm = MagicMock()
        mock_tx_cm.__aenter__ = AsyncMock(return_value=mock_tx)
        mock_tx_cm.__aexit__ = AsyncMock(return_value=None)
        
        mock_prisma = MagicMock()
        mock_prisma.tx.return_value = mock_tx_cm
        mock_get_prisma.return_value = mock_prisma
        
        yield mock_queries, mock_prisma


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
        assert hash1 != hash2


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
        assert len(parts) == 3

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
        result = _validate_competitors_format("Stripe, Twilio, Plaid")
        assert result == "Stripe, Twilio, Plaid"

    def test_validate_competitors_with_extra_spaces(self):
        result = _validate_competitors_format("  Stripe  ,  Twilio  ,  Plaid  ")
        assert result == "Stripe, Twilio, Plaid"

    def test_validate_competitors_with_special_chars(self):
        result = _validate_competitors_format("AT&T, Johnson & Johnson, 3M")
        assert result == "AT&T, Johnson & Johnson, 3M"

    def test_validate_competitors_empty_string(self):
        assert _validate_competitors_format("") is None

    def test_validate_competitors_none(self):
        assert _validate_competitors_format(None) is None

    def test_validate_competitors_whitespace_only(self):
        assert _validate_competitors_format("   ") is None

    def test_validate_competitors_invalid_chars_filtered(self):
        result = _validate_competitors_format("Valid, <script>alert('xss')</script>")
        assert result == "Valid"

    def test_validate_competitors_all_invalid_returns_none(self):
        assert _validate_competitors_format("<script>, @#$%") is None


# ============================================================================
# Test Google Token Verification
# ============================================================================


class TestGoogleTokenVerification:
    @pytest.mark.asyncio
    async def test_verify_google_token_success(self):
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
        with patch("air1.services.outreach.onboarding.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = Exception("Network error")
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await _verify_google_token("some_token")
            assert result is None


# ============================================================================
# Test Helpers
# ============================================================================


def _create_onboarding_request(test_uuid: str, auth_method: str = "email") -> OnboardingRequest:
    """Helper to create OnboardingRequest with unique data."""
    auth_data = {
        "method": auth_method,
        "email": f"test.{test_uuid}@example.com",
        "firstName": "John",
        "lastName": "Doe",
    }
    if auth_method == "email":
        auth_data["password"] = "password123"
    else:
        auth_data["googleAccessToken"] = "valid_google_token"

    return OnboardingRequest(
        auth=AuthData(**auth_data),
        company=CompanyData(
            name=f"Acme Inc {test_uuid}",
            description="We build things",
            website="https://acme.com",
            industry="Technology",
            linkedinUrl=f"https://linkedin.com/company/acme-{test_uuid}",
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
            meetingLink=f"https://cal.com/john-{test_uuid}",
        ),
    )


def _create_user_input(test_uuid: str) -> CreateUserInput:
    """Helper to create CreateUserInput with unique data."""
    return CreateUserInput(
        email=f"test.{test_uuid}@example.com",
        first_name="Test",
        last_name="User",
        auth_method="email",
        password_hash="salt:hash",
        timezone="EST",
        meeting_link=f"https://cal.com/test-{test_uuid}",
        linkedin_connected=False,
        company_name=f"Test Corp {test_uuid}",
        company_description="Test company description",
        company_website="https://test.com",
        company_industry="Technology",
        company_linkedin_url=f"https://linkedin.com/company/test-{test_uuid}",
        company_size="10-100",
        product_name="Test Product",
        product_url="https://test.com/product",
        product_description="Test product description",
        product_icp="Test ICP",
        product_competitors="Competitor1, Competitor2",
        writing_style_template="default",
        writing_style_dos=["be clear", "be concise"],
        writing_style_donts=["be verbose"],
    )


# ============================================================================
# Test Get User By Email (mock/real DB)
# ============================================================================


class TestGetUserByEmail:
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_connection, test_email):
        """Test getting user by email when user doesn't exist."""
        from air1.services.outreach.onboarding_repo import get_user_by_email

        if db_connection:
            # Real DB
            result = await get_user_by_email(test_email)
            assert result is None
        else:
            # Mocked
            with patch("air1.services.outreach.onboarding_repo.get_prisma") as mock_get_prisma, \
                 patch("air1.services.outreach.onboarding_repo.queries") as mock_queries:
                mock_prisma = AsyncMock()
                mock_get_prisma.return_value = mock_prisma
                mock_queries.get_user_by_email = AsyncMock(return_value=None)

                result = await get_user_by_email(test_email)
                assert result is None


# ============================================================================
# Test Create User With Onboarding (mock/real DB)
# ============================================================================


class TestCreateUserWithOnboarding:
    @pytest.mark.asyncio
    async def test_create_user_success(self, db_connection, test_uuid):
        """Test successful user creation with all onboarding data."""
        from air1.services.outreach.onboarding_repo import (
            create_user_with_onboarding,
            get_user_by_email,
        )

        input_data = _create_user_input(test_uuid)

        if db_connection:
            # Real DB
            success, user_id = await create_user_with_onboarding(input_data)
            assert success is True
            assert user_id is not None

            # Verify user exists
            user = await get_user_by_email(input_data.email)
            assert user is not None
            assert user["email"] == input_data.email
        else:
            # Mocked
            async with mock_db_context() as (mock_queries, mock_prisma):
                mock_queries.insert_user = AsyncMock(return_value={"userId": 999})
                mock_queries.insert_user_company = AsyncMock(return_value={"companyId": 1})
                mock_queries.insert_user_product = AsyncMock(return_value={"productId": 1})
                mock_queries.insert_user_writing_style = AsyncMock(return_value={"writingStyleId": 1})

                success, user_id = await create_user_with_onboarding(input_data)
                assert success is True
                assert user_id == 999

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_rejected(self, db_connection, test_uuid):
        """Test that duplicate email raises UserExistsError."""
        from air1.services.outreach.onboarding_repo import (
            create_user_with_onboarding,
            UserExistsError,
        )

        input_data = _create_user_input(test_uuid)

        if db_connection:
            # Real DB - create first, then try duplicate
            success, _ = await create_user_with_onboarding(input_data)
            assert success is True

            # Change linkedin URL to avoid that conflict, keep same email
            input_data.company_linkedin_url = f"https://linkedin.com/company/dup-{test_uuid}"
            with pytest.raises(UserExistsError):
                await create_user_with_onboarding(input_data)
        else:
            # Mocked
            async with mock_db_context() as (mock_queries, mock_prisma):
                mock_queries.insert_user = AsyncMock(return_value=None)  # ON CONFLICT returns None

                with pytest.raises(UserExistsError):
                    await create_user_with_onboarding(input_data)


# ============================================================================
# Test Create Onboarding User Service (mock/real DB)
# ============================================================================


class TestCreateOnboardingUserService:
    @pytest.mark.asyncio
    async def test_create_user_email_auth_success(self, db_connection, test_uuid):
        """Test successful user creation with email auth."""
        request = _create_onboarding_request(test_uuid, auth_method="email")

        if db_connection:
            # Real DB
            result = await create_onboarding_user(request)
            assert result is not None
            assert result.user.email == request.auth.email
            assert result.token is not None
            assert len(result.token.split(".")) == 3  # Valid JWT
        else:
            # Mocked
            with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
                 patch("air1.services.outreach.onboarding.create_user_with_onboarding") as mock_create, \
                 patch("air1.services.outreach.onboarding.settings") as mock_settings:

                mock_get_user.return_value = None
                mock_create.return_value = (True, 123)
                mock_settings.jwt_secret = "test-secret"
                mock_settings.jwt_expiry_hours = 24

                result = await create_onboarding_user(request)
                assert result is not None
                assert result.user.id == "123"
                assert result.user.email == request.auth.email
                assert result.token is not None

    @pytest.mark.asyncio
    async def test_create_user_email_exists_error(self, db_connection, test_uuid):
        """Test that existing email raises EmailExistsError."""
        request = _create_onboarding_request(test_uuid, auth_method="email")

        if db_connection:
            # Real DB - create first, then try duplicate
            await create_onboarding_user(request)

            # Try again with same email
            with pytest.raises(EmailExistsError):
                await create_onboarding_user(request)
        else:
            # Mocked
            with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user:
                mock_get_user.return_value = {"user_id": 1, "email": request.auth.email}

                with pytest.raises(EmailExistsError):
                    await create_onboarding_user(request)

    @pytest.mark.asyncio
    async def test_create_user_google_auth_success(self, db_connection, test_uuid):
        """Test successful user creation with Google auth."""
        request = _create_onboarding_request(test_uuid, auth_method="google")

        # Google auth always needs token verification mocked (we can't get real Google tokens)
        with patch("air1.services.outreach.onboarding._verify_google_token") as mock_verify:
            mock_verify.return_value = {"email": request.auth.email}

            if db_connection:
                # Real DB
                result = await create_onboarding_user(request)
                assert result is not None
                assert result.user.email == request.auth.email
                assert result.token is not None
            else:
                # Mocked
                with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
                     patch("air1.services.outreach.onboarding.create_user_with_onboarding") as mock_create, \
                     patch("air1.services.outreach.onboarding.settings") as mock_settings:

                    mock_get_user.return_value = None
                    mock_create.return_value = (True, 456)
                    mock_settings.jwt_secret = "test-secret"
                    mock_settings.jwt_expiry_hours = 24

                    result = await create_onboarding_user(request)
                    assert result is not None
                    assert result.user.id == "456"

    @pytest.mark.asyncio
    async def test_create_user_invalid_google_token(self, db_connection, test_uuid):
        """Test that invalid Google token raises InvalidGoogleTokenError."""
        request = _create_onboarding_request(test_uuid, auth_method="google")

        with patch("air1.services.outreach.onboarding._verify_google_token") as mock_verify:
            mock_verify.return_value = None  # Invalid token

            if db_connection:
                # Real DB - still raises because token verification fails
                with pytest.raises(InvalidGoogleTokenError):
                    await create_onboarding_user(request)
            else:
                # Mocked
                with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user:
                    mock_get_user.return_value = None

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
