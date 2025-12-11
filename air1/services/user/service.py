"""User service for account management."""

import base64
import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from air1.config import settings
from air1.services.user.account_repo import (
    get_account_by_user_id as _get_account_by_user_id,
    update_user_profile as _update_user_profile,
)


@dataclass
class AuthUser:
    """Authenticated user from JWT token."""

    user_id: int
    email: str


class IUserService(ABC):
    """Service interface for user account management."""

    @abstractmethod
    async def get_account(self, user_id: int) -> Optional[dict]:
        """
        Get account data by user ID.

        Args:
            user_id: The user's ID

        Returns:
            Account data dict or None if not found
        """
        pass

    @abstractmethod
    async def update_profile(
        self,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> bool:
        """
        Update user profile fields. Only non-None values are updated.

        Args:
            user_id: The user's ID
            first_name: New first name
            last_name: New last name
            timezone: New timezone
            meeting_link: New meeting link URL

        Returns:
            True if update succeeded, False otherwise
        """
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[AuthUser]:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT token string

        Returns:
            AuthUser if valid, None otherwise
        """
        pass


class UserService(IUserService):
    """Concrete implementation of user service."""

    async def get_account(self, user_id: int) -> Optional[dict]:
        """Get account data by user ID."""
        return await _get_account_by_user_id(user_id)

    async def update_profile(
        self,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> bool:
        """Update user profile fields."""
        return await _update_user_profile(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            timezone=timezone,
            meeting_link=meeting_link,
        )

    def verify_token(self, token: str) -> Optional[AuthUser]:
        """Verify and decode a JWT token."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts

            # Verify signature
            expected_signature = hmac.new(
                settings.jwt_secret.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256,
            ).digest()
            expected_signature_b64 = (
                base64.urlsafe_b64encode(expected_signature).rstrip(b"=").decode()
            )

            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return None

            # Decode payload (add padding if needed)
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload = json.loads(base64.urlsafe_b64decode(payload_b64))

            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None

            user_id = int(payload.get("sub", 0))
            email = payload.get("email", "")

            if not user_id:
                return None

            return AuthUser(user_id=user_id, email=email)
        except Exception:
            return None
