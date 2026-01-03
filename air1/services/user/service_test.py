"""
Tests for the User Service.

Run with:
    pytest air1/services/user/service_test.py -v -s
"""

import pytest
import uuid
from loguru import logger

from air1.services.user.service import Service


class TestService:
    """Tests for the Service class."""

    @pytest.fixture
    def service(self):
        """Create a Service instance for testing."""
        return Service()

    @pytest.fixture
    def unique_clerk_id(self):
        """Generate a unique clerk_id for each test."""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @pytest.mark.asyncio
    async def test_get_or_create_account_creates_new_user(self, service, unique_clerk_id, db_connection):
        """Test creating account for new user."""
        email = f"{unique_clerk_id}@test.example.com"

        result = await service.get_or_create_account(
            clerk_id=unique_clerk_id,
            email=email,
        )

        assert result is not None
        assert result["clerk_id"] == unique_clerk_id
        assert result["email"] == email
        assert result["user_id"] is not None
        logger.success(f"✓ Created new user with clerk_id: {unique_clerk_id}")

    @pytest.mark.asyncio
    async def test_get_or_create_account_returns_existing_user(self, service, unique_clerk_id, db_connection):
        """Test getting account for existing user."""
        email = f"{unique_clerk_id}@test.example.com"

        # Create user first
        created = await service.get_or_create_account(
            clerk_id=unique_clerk_id,
            email=email,
        )
        assert created is not None
        original_user_id = created["user_id"]

        # Get same user again
        result = await service.get_or_create_account(
            clerk_id=unique_clerk_id,
            email=email,
        )

        assert result is not None
        assert result["user_id"] == original_user_id
        assert result["clerk_id"] == unique_clerk_id
        logger.success("✓ Retrieved existing user correctly")

    @pytest.mark.asyncio
    async def test_update_profile_success(self, service, unique_clerk_id, db_connection):
        """Test successful profile update."""
        email = f"{unique_clerk_id}@test.example.com"

        # Create user first
        await service.get_or_create_account(clerk_id=unique_clerk_id, email=email)

        # Update profile
        result = await service.update_profile(
            clerk_id=unique_clerk_id,
            first_name="Test",
            last_name="User",
            timezone="America/New_York",
            meeting_link="https://cal.com/test/30min",
        )

        assert result is True

        # Verify update
        account = await service.get_or_create_account(clerk_id=unique_clerk_id, email=email)
        assert account["first_name"] == "Test"
        assert account["last_name"] == "User"
        assert account["timezone"] == "America/New_York"
        assert account["meeting_link"] == "https://cal.com/test/30min"
        logger.success("✓ Profile updated successfully")

    @pytest.mark.asyncio
    async def test_update_profile_partial(self, service, unique_clerk_id, db_connection):
        """Test partial profile update (only some fields)."""
        email = f"{unique_clerk_id}@test.example.com"

        # Create user and set initial values
        await service.get_or_create_account(clerk_id=unique_clerk_id, email=email)
        await service.update_profile(
            clerk_id=unique_clerk_id,
            first_name="Original",
            last_name="Name",
            timezone="UTC",
        )

        # Partial update - only timezone
        result = await service.update_profile(
            clerk_id=unique_clerk_id,
            timezone="Europe/London",
        )

        assert result is True

        # Verify only timezone changed
        account = await service.get_or_create_account(clerk_id=unique_clerk_id, email=email)
        assert account["first_name"] == "Original"  # Unchanged
        assert account["last_name"] == "Name"  # Unchanged
        assert account["timezone"] == "Europe/London"  # Changed
        logger.success("✓ Partial update works correctly")

    @pytest.mark.asyncio
    async def test_update_profile_nonexistent_user(self, service, db_connection):
        """Test updating profile for non-existent user."""
        result = await service.update_profile(
            clerk_id="user_nonexistent_12345",
            first_name="Ghost",
        )

        # Should still return True (UPDATE affects 0 rows but doesn't fail)
        assert result is True
        logger.success("✓ Update for non-existent user handled gracefully")
