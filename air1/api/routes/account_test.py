"""
Tests for the Account API endpoints.

Run with mocks (default):
    pytest air1/api/routes/account_test.py -v -s

Run against real database:
    pytest air1/api/routes/account_test.py --use-real-db -v -s
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from loguru import logger

from air1.app import app
from air1.services.outreach.onboarding import _create_jwt


def create_test_token(user_id: int = 1, email: str = "test@example.com") -> str:
    """Create a valid JWT token for testing."""
    return _create_jwt(user_id, email)


class TestGetAccount:
    @pytest.mark.asyncio
    async def test_get_account_success(self, db_connection):
        """Test successful account retrieval."""
        mock_account_data = {
            "user_id": 1,
            "email": "ali@hodhod.ai",
            "first_name": "Ali",
            "last_name": "Abbassi",
            "timezone": "EST",
            "meeting_link": "https://cal.com/ali/30min",
            "linkedin_connected": True,
            "company_id": 1,
            "company_name": "HODHOD",
            "company_linkedin_username": "hodhod-ai",
        }

        token = create_test_token(user_id=1, email="ali@hodhod.ai")

        with patch("air1.api.routes.account.user_service") as mock_service:
            mock_service.get_account = AsyncMock(return_value=mock_account_data)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/account",
                    headers={"Authorization": f"Bearer {token}"},
                )

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.json()}")

            assert response.status_code == 200
            data = response.json()

            assert data["user"]["id"] == "1"
            assert data["user"]["email"] == "ali@hodhod.ai"
            assert data["user"]["firstName"] == "Ali"
            assert data["user"]["lastName"] == "Abbassi"
            assert data["user"]["timezone"] == "EST"
            assert data["user"]["meetingLink"] == "https://cal.com/ali/30min"

            assert data["linkedin"]["connected"] is True
            assert data["linkedin"]["profileUrl"] == "https://linkedin.com/in/hodhod-ai"
            assert data["linkedin"]["dailyLimits"]["connections"] == 25
            assert data["linkedin"]["dailyLimits"]["inmails"] == 40

            assert data["company"]["id"] == "1"
            assert data["company"]["name"] == "HODHOD"
            assert data["company"]["plan"] == "free"

            logger.success("✓ GET /api/account returns correct data")

    @pytest.mark.asyncio
    async def test_get_account_unauthorized_no_token(self):
        """Test that missing token returns 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/account")

        logger.info(f"Response status: {response.status_code}")

        assert response.status_code in [401, 403]
        logger.success("✓ Missing token correctly returns 401/403")

    @pytest.mark.asyncio
    async def test_get_account_unauthorized_invalid_token(self):
        """Test that invalid token returns 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/account",
                headers={"Authorization": "Bearer invalid.token.here"},
            )

        logger.info(f"Response status: {response.status_code}")

        assert response.status_code == 401
        logger.success("✓ Invalid token correctly returns 401")

    @pytest.mark.asyncio
    async def test_get_account_not_found(self):
        """Test that non-existent account returns 404."""
        token = create_test_token(user_id=99999, email="notfound@example.com")

        with patch("air1.api.routes.account.user_service") as mock_service:
            mock_service.get_account = AsyncMock(return_value=None)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/account",
                    headers={"Authorization": f"Bearer {token}"},
                )

        logger.info(f"Response status: {response.status_code}")

        assert response.status_code == 404
        logger.success("✓ Non-existent account correctly returns 404")


class TestUpdateAccount:
    @pytest.mark.asyncio
    async def test_update_account_success(self):
        """Test successful account update."""
        mock_account_data = {
            "user_id": 1,
            "email": "ali@hodhod.ai",
            "first_name": "Ali",
            "last_name": "Hassan",
            "timezone": "PST",
            "meeting_link": "https://cal.com/ali/30min",
            "linkedin_connected": True,
            "company_id": 1,
            "company_name": "HODHOD",
            "company_linkedin_username": "hodhod-ai",
        }

        token = create_test_token(user_id=1, email="ali@hodhod.ai")

        with patch("air1.api.routes.account.user_service") as mock_service:
            mock_service.update_profile = AsyncMock(return_value=True)
            mock_service.get_account = AsyncMock(return_value=mock_account_data)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.patch(
                    "/api/account",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "firstName": "Ali",
                        "lastName": "Hassan",
                        "timezone": "PST",
                    },
                )

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.json()}")

            assert response.status_code == 200
            data = response.json()
            assert data["user"]["lastName"] == "Hassan"
            assert data["user"]["timezone"] == "PST"

            mock_service.update_profile.assert_called_once()
            logger.success("✓ PATCH /api/account updates correctly")

    @pytest.mark.asyncio
    async def test_update_account_partial(self):
        """Test partial account update (only timezone)."""
        mock_account_data = {
            "user_id": 1,
            "email": "ali@hodhod.ai",
            "first_name": "Ali",
            "last_name": "Abbassi",
            "timezone": "GMT",
            "meeting_link": "https://cal.com/ali/30min",
            "linkedin_connected": True,
            "company_id": 1,
            "company_name": "HODHOD",
            "company_linkedin_username": None,
        }

        token = create_test_token(user_id=1, email="ali@hodhod.ai")

        with patch("air1.api.routes.account.user_service") as mock_service:
            mock_service.update_profile = AsyncMock(return_value=True)
            mock_service.get_account = AsyncMock(return_value=mock_account_data)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.patch(
                    "/api/account",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"timezone": "GMT"},
                )

            assert response.status_code == 200
            logger.success("✓ Partial update works correctly")

    @pytest.mark.asyncio
    async def test_update_account_invalid_meeting_link(self):
        """Test that invalid meeting link URL returns 422."""
        token = create_test_token(user_id=1, email="ali@hodhod.ai")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/account",
                headers={"Authorization": f"Bearer {token}"},
                json={"meetingLink": "not-a-valid-url"},
            )

        logger.info(f"Response status: {response.status_code}")

        assert response.status_code == 422
        logger.success("✓ Invalid meeting link correctly returns 422")

    @pytest.mark.asyncio
    async def test_update_account_empty_body(self):
        """Test that empty request body returns 400."""
        token = create_test_token(user_id=1, email="ali@hodhod.ai")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/account",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )

        logger.info(f"Response status: {response.status_code}")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "VALIDATION_ERROR"
        logger.success("✓ Empty body correctly returns 400")

    @pytest.mark.asyncio
    async def test_update_account_unauthorized(self):
        """Test that missing token returns 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/account",
                json={"firstName": "Test"},
            )

        assert response.status_code in [401, 403]
        logger.success("✓ Missing token correctly returns 401/403")
