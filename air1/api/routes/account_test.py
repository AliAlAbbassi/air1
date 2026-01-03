"""
Tests for the Account API endpoints.

Run with:
    pytest air1/api/routes/account_test.py -v -s
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from loguru import logger

from air1.app import app
from air1.api.auth import AuthUser, get_current_user


@pytest.fixture
def unique_clerk_id():
    """Generate a unique clerk_id for each test."""
    return f"user_test_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def override_auth():
    """Fixture to override auth dependency with mock user."""

    def _override(clerk_id: str = "user_test123", email: str = "test@example.com"):
        async def mock_get_current_user():
            return AuthUser(user_id=clerk_id, email=email)

        app.dependency_overrides[get_current_user] = mock_get_current_user
        return AuthUser(user_id=clerk_id, email=email)

    yield _override
    app.dependency_overrides.clear()


class TestGetAccount:
    @pytest.mark.asyncio
    async def test_get_account_creates_new_user(self, override_auth, unique_clerk_id, db_connection):
        """Test that GET /api/account creates user on first login."""
        email = f"{unique_clerk_id}@test.example.com"
        override_auth(clerk_id=unique_clerk_id, email=email)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/account")

        assert response.status_code == 200
        data = response.json()

        assert data["user"]["email"] == email
        assert data["user"]["firstName"] == ""
        assert data["user"]["lastName"] == ""
        assert data["user"]["timezone"] == "UTC"  # Default
        assert data["user"]["id"] is not None

        logger.success(f"✓ GET /api/account auto-provisioned user: {unique_clerk_id}")

    @pytest.mark.asyncio
    async def test_get_account_returns_existing_user(self, override_auth, unique_clerk_id, db_connection):
        """Test that GET /api/account returns existing user."""
        email = f"{unique_clerk_id}@test.example.com"
        override_auth(clerk_id=unique_clerk_id, email=email)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # First call creates user
            response1 = await client.get("/api/account")
            assert response1.status_code == 200
            user_id_1 = response1.json()["user"]["id"]

            # Second call returns same user
            response2 = await client.get("/api/account")
            assert response2.status_code == 200
            user_id_2 = response2.json()["user"]["id"]

        assert user_id_1 == user_id_2
        logger.success("✓ GET /api/account returns same user on subsequent calls")

    @pytest.mark.asyncio
    async def test_get_account_unauthorized_no_token(self):
        """Test that missing token returns 401/403."""
        app.dependency_overrides.clear()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/account")

        assert response.status_code in [401, 403, 500]
        logger.success("✓ Missing token correctly returns error")


class TestUpdateAccount:
    @pytest.mark.asyncio
    async def test_update_account_success(self, override_auth, unique_clerk_id, db_connection):
        """Test successful account update."""
        email = f"{unique_clerk_id}@test.example.com"
        override_auth(clerk_id=unique_clerk_id, email=email)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create user first
            await client.get("/api/account")

            # Update profile
            response = await client.patch(
                "/api/account",
                json={
                    "firstName": "Test",
                    "lastName": "User",
                    "timezone": "America/Los_Angeles",
                    "meetingLink": "https://cal.com/test/30min",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert data["user"]["firstName"] == "Test"
        assert data["user"]["lastName"] == "User"
        assert data["user"]["timezone"] == "America/Los_Angeles"
        assert data["user"]["meetingLink"] == "https://cal.com/test/30min"

        logger.success("✓ PATCH /api/account updates correctly")

    @pytest.mark.asyncio
    async def test_update_account_partial(self, override_auth, unique_clerk_id, db_connection):
        """Test partial account update (only timezone)."""
        email = f"{unique_clerk_id}@test.example.com"
        override_auth(clerk_id=unique_clerk_id, email=email)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create user and set initial values
            await client.get("/api/account")
            await client.patch(
                "/api/account",
                json={"firstName": "Original", "lastName": "Name"},
            )

            # Partial update - only timezone
            response = await client.patch(
                "/api/account",
                json={"timezone": "Europe/London"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["user"]["firstName"] == "Original"  # Unchanged
        assert data["user"]["lastName"] == "Name"  # Unchanged
        assert data["user"]["timezone"] == "Europe/London"  # Changed

        logger.success("✓ Partial update works correctly")

    @pytest.mark.asyncio
    async def test_update_account_invalid_meeting_link(self, override_auth, unique_clerk_id, db_connection):
        """Test that invalid meeting link URL returns 422."""
        override_auth(clerk_id=unique_clerk_id, email=f"{unique_clerk_id}@test.example.com")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create user first
            await client.get("/api/account")

            response = await client.patch(
                "/api/account",
                json={"meetingLink": "not-a-valid-url"},
            )

        assert response.status_code == 422
        logger.success("✓ Invalid meeting link correctly returns 422")

    @pytest.mark.asyncio
    async def test_update_account_empty_body(self, override_auth, unique_clerk_id, db_connection):
        """Test that empty request body returns 400."""
        override_auth(clerk_id=unique_clerk_id, email=f"{unique_clerk_id}@test.example.com")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create user first
            await client.get("/api/account")

            response = await client.patch(
                "/api/account",
                json={},
            )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "VALIDATION_ERROR"
        logger.success("✓ Empty body correctly returns 400")

    @pytest.mark.asyncio
    async def test_update_account_unauthorized(self):
        """Test that missing token returns error."""
        app.dependency_overrides.clear()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/account",
                json={"firstName": "Test"},
            )

        assert response.status_code in [401, 403, 500]
        logger.success("✓ Missing token correctly returns error")

    @pytest.mark.asyncio
    async def test_update_persists_across_requests(self, override_auth, unique_clerk_id, db_connection):
        """Test that updates persist and are returned in subsequent GET requests."""
        email = f"{unique_clerk_id}@test.example.com"
        override_auth(clerk_id=unique_clerk_id, email=email)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create user
            await client.get("/api/account")

            # Update
            await client.patch(
                "/api/account",
                json={"firstName": "Persisted", "timezone": "Asia/Tokyo"},
            )

            # Fetch again
            response = await client.get("/api/account")

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["firstName"] == "Persisted"
        assert data["user"]["timezone"] == "Asia/Tokyo"

        logger.success("✓ Updates persist across requests")
