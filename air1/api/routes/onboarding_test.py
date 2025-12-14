"""
End-to-end tests for the onboarding API endpoint.

Tests the full flow: API request -> validation -> service -> database

Run with mocks (default):
    pytest air1/api/routes/onboarding_test.py -v -s

Run against real database:
    pytest air1/api/routes/onboarding_test.py --use-real-db -v -s
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from loguru import logger

from air1.app import app


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def test_uuid():
    """Generate unique UUID for test data."""
    return str(uuid.uuid4())[:8]


async def cleanup_test_data():
    """Delete all test users created by these tests (emails matching test.%@example.com)."""
    from air1.db.prisma_client import get_prisma, connect_db
    
    try:
        await connect_db()
        prisma = await get_prisma()
        
        # Get all test user IDs
        users = await prisma.query_raw(
            "SELECT user_id FROM hodhod_user WHERE email LIKE 'test.%@example.com'"
        )
        
        if not users:
            logger.info("No test users to cleanup")
            return
            
        user_ids = [u["user_id"] for u in users]
        logger.info(f"Cleaning up {len(user_ids)} test users...")
        
        # Delete in order due to FK constraints
        for user_id in user_ids:
            await prisma.execute_raw("DELETE FROM writing_style WHERE user_id = $1", user_id)
            await prisma.execute_raw("DELETE FROM product WHERE user_id = $1", user_id)
            await prisma.execute_raw("DELETE FROM company WHERE user_id = $1", user_id)
            await prisma.execute_raw("DELETE FROM hodhod_user WHERE user_id = $1", user_id)
        
        logger.success(f"✓ Cleaned up {len(user_ids)} test users")
    except Exception as e:
        logger.warning(f"Failed to cleanup test data: {e}")


@pytest.fixture(scope="module", autouse=True)
def cleanup_after_tests(request):
    """Cleanup test data after all tests in this module complete."""
    yield
    
    # Only cleanup if using real DB
    if request.config.getoption("--use-real-db", default=False):
        import asyncio
        asyncio.get_event_loop().run_until_complete(cleanup_test_data())


def create_valid_onboarding_payload(test_uuid: str, auth_method: str = "email") -> dict:
    """Create a valid onboarding request payload."""
    payload = {
        "auth": {
            "method": auth_method,
            "email": f"test.{test_uuid}@example.com",
            "firstName": "John",
            "lastName": "Doe",
        },
        "company": {
            "name": f"Test Company {test_uuid}",
            "description": "A test company for unit testing",
            "website": "https://testcompany.com",
            "industry": "Technology",
            "linkedinUrl": f"https://linkedin.com/company/test-{test_uuid}",
            "employeeCount": "10-100",
        },
        "product": {
            "name": "Test Product",
            "url": "https://testcompany.com/product",
            "description": "A test product for unit testing",
            "idealCustomerProfile": "Engineering leaders at tech companies",
            "competitors": "Competitor1, Competitor2",
        },
        "writingStyle": {
            "selectedTemplate": "professional",
            "dos": ["be clear", "be concise"],
            "donts": ["use jargon", "be verbose"],
        },
        "linkedin": {
            "connected": False,
        },
        "profile": {
            "timezone": "America/New_York",
            "meetingLink": f"https://cal.com/test-{test_uuid}",
        },
    }

    if auth_method == "email":
        payload["auth"]["password"] = "securepassword123"
    else:
        payload["auth"]["googleAccessToken"] = "mock_google_token_12345"

    return payload


def create_payload_with_empty_optional_fields(test_uuid: str) -> dict:
    """Create payload with empty optional fields (website, industry, description)."""
    return {
        "auth": {
            "method": "email",
            "email": f"test.{test_uuid}@example.com",
            "firstName": "Jane",
            "lastName": "Smith",
            "password": "securepassword123",
        },
        "company": {
            "name": f"Minimal Company {test_uuid}",
            "description": "",  # Empty - should be allowed
            "website": "",  # Empty - should be allowed
            "industry": "",  # Empty - should be allowed
            "linkedinUrl": f"https://linkedin.com/company/minimal-{test_uuid}",
            "employeeCount": "0-10",
        },
        "product": {
            "name": "Minimal Product",
            "url": "https://minimal.com/product",
            "description": "Minimal product description",
            "idealCustomerProfile": "Anyone",
        },
        "writingStyle": {
            "dos": [],
            "donts": [],
        },
        "linkedin": {
            "connected": False,
        },
        "profile": {
            "timezone": "UTC",
            "meetingLink": f"https://cal.com/minimal-{test_uuid}",
        },
    }


# ============================================================================
# Test API Endpoint - Email Auth
# ============================================================================


class TestOnboardingAPIEmailAuth:
    @pytest.mark.asyncio
    async def test_create_account_email_auth_success(self, db_connection, test_uuid):
        """Test successful account creation with email authentication."""
        payload = create_valid_onboarding_payload(test_uuid, auth_method="email")

        logger.info(f"Testing email auth with payload: {payload}")

        if db_connection:
            # Real DB test
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/onboarding", json=payload)

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.json()}")

            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"

            data = response.json()
            assert "user" in data
            assert "token" in data
            assert data["user"]["email"] == payload["auth"]["email"]
            assert data["user"]["firstName"] == payload["auth"]["firstName"]
            assert data["user"]["lastName"] == payload["auth"]["lastName"]
            assert len(data["token"].split(".")) == 3  # Valid JWT format

            logger.success(f"✓ Account created successfully with user_id: {data['user']['id']}")
        else:
            # Mocked test
            with patch("air1.api.routes.onboarding.Service") as MockService:
                mock_service = AsyncMock()
                mock_service.create_onboarding_user.return_value = {
                    "user": {
                        "id": "123",
                        "email": payload["auth"]["email"],
                        "firstName": payload["auth"]["firstName"],
                        "lastName": payload["auth"]["lastName"],
                    },
                    "token": "mock.jwt.token",
                }

                mock_context = AsyncMock()
                mock_context.__aenter__.return_value = mock_service
                mock_context.__aexit__.return_value = None
                MockService.return_value = mock_context

                # For mocked tests, we need to mock the actual service function
                with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
                     patch("air1.services.outreach.onboarding.create_user_with_onboarding") as mock_create, \
                     patch("air1.services.outreach.onboarding.settings") as mock_settings:

                    mock_get_user.return_value = None
                    mock_create.return_value = (True, 123)
                    mock_settings.jwt_secret = "test-secret"
                    mock_settings.jwt_expiry_hours = 24

                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        response = await client.post("/api/onboarding", json=payload)

                    logger.info(f"Response status: {response.status_code}")
                    logger.info(f"Response body: {response.json()}")

                    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
                    logger.success("✓ Mocked account creation successful")

    @pytest.mark.asyncio
    async def test_create_account_with_empty_optional_fields(self, db_connection, test_uuid):
        """Test account creation with empty website, industry, description."""
        payload = create_payload_with_empty_optional_fields(test_uuid)

        logger.info(f"Testing with empty optional fields: {payload}")

        if db_connection:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/onboarding", json=payload)

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.json()}")

            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"

            data = response.json()
            assert data["user"]["email"] == payload["auth"]["email"]
            logger.success("✓ Account created with empty optional fields")
        else:
            with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
                 patch("air1.services.outreach.onboarding.create_user_with_onboarding") as mock_create, \
                 patch("air1.services.outreach.onboarding.settings") as mock_settings:

                mock_get_user.return_value = None
                mock_create.return_value = (True, 456)
                mock_settings.jwt_secret = "test-secret"
                mock_settings.jwt_expiry_hours = 24

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post("/api/onboarding", json=payload)

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response body: {response.json()}")

                assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
                logger.success("✓ Mocked account creation with empty optional fields successful")


# ============================================================================
# Test API Endpoint - Google Auth
# ============================================================================


class TestOnboardingAPIGoogleAuth:
    @pytest.mark.asyncio
    async def test_create_account_google_auth_success(self, db_connection, test_uuid):
        """Test successful account creation with Google authentication."""
        payload = create_valid_onboarding_payload(test_uuid, auth_method="google")

        logger.info(f"Testing Google auth with payload: {payload}")

        # Always mock Google token verification
        with patch("air1.services.outreach.onboarding._verify_google_token") as mock_verify:
            mock_verify.return_value = {"email": payload["auth"]["email"]}

            if db_connection:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post("/api/onboarding", json=payload)

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response body: {response.json()}")

                assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"

                data = response.json()
                assert data["user"]["email"] == payload["auth"]["email"]
                logger.success(f"✓ Google auth account created with user_id: {data['user']['id']}")
            else:
                with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
                     patch("air1.services.outreach.onboarding.create_user_with_onboarding") as mock_create, \
                     patch("air1.services.outreach.onboarding.settings") as mock_settings:

                    mock_get_user.return_value = None
                    mock_create.return_value = (True, 789)
                    mock_settings.jwt_secret = "test-secret"
                    mock_settings.jwt_expiry_hours = 24

                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        response = await client.post("/api/onboarding", json=payload)

                    logger.info(f"Response status: {response.status_code}")
                    logger.info(f"Response body: {response.json()}")

                    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
                    logger.success("✓ Mocked Google auth account creation successful")

    @pytest.mark.asyncio
    async def test_create_account_invalid_google_token(self, db_connection, test_uuid):
        """Test that invalid Google token returns 400 error."""
        payload = create_valid_onboarding_payload(test_uuid, auth_method="google")

        with patch("air1.services.outreach.onboarding._verify_google_token") as mock_verify:
            mock_verify.return_value = None  # Invalid token

            if db_connection:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post("/api/onboarding", json=payload)

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response body: {response.json()}")

                assert response.status_code == 400
                data = response.json()
                error = data.get("error") or data.get("detail", {}).get("error")
                assert error == "INVALID_GOOGLE_TOKEN"
                logger.success("✓ Invalid Google token correctly rejected")
            else:
                with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user:
                    mock_get_user.return_value = None

                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        response = await client.post("/api/onboarding", json=payload)

                    assert response.status_code == 400
                    logger.success("✓ Mocked invalid Google token correctly rejected")


# ============================================================================
# Test API Endpoint - Validation Errors
# ============================================================================


class TestOnboardingAPIValidation:
    @pytest.mark.asyncio
    async def test_missing_required_field_returns_422(self, test_uuid):
        """Test that missing required fields return 422 with details."""
        payload = create_valid_onboarding_payload(test_uuid)
        del payload["auth"]["email"]  # Remove required field

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/onboarding", json=payload)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.json()}")

        assert response.status_code == 422
        data = response.json()
        assert "details" in data
        logger.success("✓ Missing required field correctly returns 422")

    @pytest.mark.asyncio
    async def test_invalid_email_format_returns_422(self, test_uuid):
        """Test that invalid email format returns 422."""
        payload = create_valid_onboarding_payload(test_uuid)
        payload["auth"]["email"] = "not-an-email"

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/onboarding", json=payload)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.json()}")

        assert response.status_code == 422
        logger.success("✓ Invalid email format correctly returns 422")

    @pytest.mark.asyncio
    async def test_invalid_linkedin_url_returns_422(self, test_uuid):
        """Test that invalid LinkedIn URL returns 422."""
        payload = create_valid_onboarding_payload(test_uuid)
        payload["company"]["linkedinUrl"] = "https://example.com/not-linkedin"

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/onboarding", json=payload)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.json()}")

        assert response.status_code == 422
        logger.success("✓ Invalid LinkedIn URL correctly returns 422")

    @pytest.mark.asyncio
    async def test_password_too_short_returns_422(self, test_uuid):
        """Test that password shorter than 8 chars returns 422."""
        payload = create_valid_onboarding_payload(test_uuid)
        payload["auth"]["password"] = "short"

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/onboarding", json=payload)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.json()}")

        assert response.status_code == 422
        logger.success("✓ Short password correctly returns 422")

    @pytest.mark.asyncio
    async def test_email_auth_without_password_returns_422(self, test_uuid):
        """Test that email auth without password returns 422."""
        payload = create_valid_onboarding_payload(test_uuid, auth_method="email")
        del payload["auth"]["password"]

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/onboarding", json=payload)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.json()}")

        assert response.status_code == 422
        logger.success("✓ Email auth without password correctly returns 422")


# ============================================================================
# Test API Endpoint - Duplicate Email
# ============================================================================


class TestOnboardingAPIDuplicateEmail:
    @pytest.mark.asyncio
    async def test_duplicate_email_returns_409(self, db_connection, test_uuid):
        """Test that duplicate email returns 409 conflict."""
        payload = create_valid_onboarding_payload(test_uuid)

        if db_connection:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # First request - should succeed
                response1 = await client.post("/api/onboarding", json=payload)
                logger.info(f"First request status: {response1.status_code}")
                assert response1.status_code == 201

                # Change linkedin URL to avoid that conflict
                payload["company"]["linkedinUrl"] = f"https://linkedin.com/company/dup-{test_uuid}"

                # Second request with same email - should fail
                response2 = await client.post("/api/onboarding", json=payload)
                logger.info(f"Second request status: {response2.status_code}")
                logger.info(f"Second request body: {response2.json()}")

                assert response2.status_code == 409
                data = response2.json()
                error = data.get("error") or data.get("detail", {}).get("error")
                assert error == "EMAIL_EXISTS"
                logger.success("✓ Duplicate email correctly returns 409")
        else:
            with patch("air1.services.outreach.onboarding.get_user_by_email") as mock_get_user, \
                 patch("air1.services.outreach.onboarding.settings") as mock_settings:

                mock_get_user.return_value = {"user_id": 1, "email": payload["auth"]["email"]}
                mock_settings.jwt_secret = "test-secret"
                mock_settings.jwt_expiry_hours = 24

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post("/api/onboarding", json=payload)

                assert response.status_code == 409
                logger.success("✓ Mocked duplicate email correctly returns 409")
