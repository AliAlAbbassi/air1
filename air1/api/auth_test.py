"""
Tests for the Auth module (Clerk integration).

Run with:
    pytest air1/api/auth_test.py -v -s
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from air1.api.auth import AuthUser, get_current_user, _starlette_to_httpx_request


class TestAuthUser:
    """Tests for the AuthUser dataclass."""

    def test_auth_user_creation(self):
        """Test creating an AuthUser."""
        user = AuthUser(user_id="user_abc123", email="test@example.com")
        assert user.user_id == "user_abc123"
        assert user.email == "test@example.com"

    def test_auth_user_optional_email(self):
        """Test AuthUser with no email."""
        user = AuthUser(user_id="user_abc123")
        assert user.user_id == "user_abc123"
        assert user.email is None


class TestStarletteToHttpxRequest:
    """Tests for request conversion."""

    def test_converts_request_correctly(self):
        """Test that Starlette request is converted to httpx request."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "http://localhost:8000/api/account"
        mock_request.headers = {"Authorization": "Bearer token123"}

        result = _starlette_to_httpx_request(mock_request)

        assert result.method == "GET"
        assert str(result.url) == "http://localhost:8000/api/account"
        assert result.headers["Authorization"] == "Bearer token123"


class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_missing_clerk_secret_raises_500(self):
        """Test that missing CLERK_SECRET_KEY raises 500."""
        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "some_token"

        with patch("air1.api.auth._clerk", None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_credentials)

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail["error"] == "CONFIG_ERROR"

    @pytest.mark.asyncio
    async def test_valid_token_returns_auth_user(self):
        """Test that valid token returns AuthUser."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "http://localhost:8000/api/account"
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        mock_request_state = MagicMock()
        mock_request_state.is_signed_in = True
        mock_request_state.payload = {
            "sub": "user_abc123",
            "email": "test@example.com",
        }

        mock_clerk = MagicMock()
        mock_clerk.authenticate_request.return_value = mock_request_state

        with patch("air1.api.auth._clerk", mock_clerk):
            result = await get_current_user(mock_request, mock_credentials)

            assert isinstance(result, AuthUser)
            assert result.user_id == "user_abc123"
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Test that invalid token raises 401."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "http://localhost:8000/api/account"
        mock_request.headers = {"Authorization": "Bearer invalid_token"}

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        mock_request_state = MagicMock()
        mock_request_state.is_signed_in = False
        mock_request_state.reason = "Token expired"

        mock_clerk = MagicMock()
        mock_clerk.authenticate_request.return_value = mock_request_state

        with patch("air1.api.auth._clerk", mock_clerk):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_credentials)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["error"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_missing_user_id_raises_401(self):
        """Test that token without user_id raises 401."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "http://localhost:8000/api/account"
        mock_request.headers = {"Authorization": "Bearer token"}

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        mock_request_state = MagicMock()
        mock_request_state.is_signed_in = True
        mock_request_state.payload = {
            "sub": "",  # Empty user_id
            "email": "test@example.com",
        }

        mock_clerk = MagicMock()
        mock_clerk.authenticate_request.return_value = mock_request_state

        with patch("air1.api.auth._clerk", mock_clerk):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_credentials)

            assert exc_info.value.status_code == 401
            assert "Invalid token payload" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_clerk_exception_raises_401(self):
        """Test that Clerk SDK exception raises 401."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "http://localhost:8000/api/account"
        mock_request.headers = {"Authorization": "Bearer token"}

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        mock_clerk = MagicMock()
        mock_clerk.authenticate_request.side_effect = Exception("Clerk error")

        with patch("air1.api.auth._clerk", mock_clerk):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_credentials)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["error"] == "UNAUTHORIZED"

