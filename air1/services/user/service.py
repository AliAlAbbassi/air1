"""User service for account management."""

from abc import ABC, abstractmethod
from typing import Optional

from air1.services.user.account_repo import (
    get_or_create_user_by_clerk_id as _get_or_create_user_by_clerk_id,
    update_user_profile_by_clerk_id as _update_user_profile_by_clerk_id,
)


class IService(ABC):
    """Service interface for user account management."""

    @abstractmethod
    async def get_or_create_account(self, clerk_id: str, email: str) -> Optional[dict]:
        """
        Get account data by Clerk ID, creating user if not exists.

        Args:
            clerk_id: The Clerk user ID
            email: User's email (used when creating new user)

        Returns:
            Account data dict or None if failed
        """
        pass

    @abstractmethod
    async def update_profile(
        self,
        clerk_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> bool:
        """
        Update user profile fields. Only non-None values are updated.

        Args:
            clerk_id: The Clerk user ID
            first_name: New first name
            last_name: New last name
            timezone: New timezone
            meeting_link: New meeting link URL

        Returns:
            True if update succeeded, False otherwise
        """
        pass


class Service(IService):
    """Concrete implementation of user service."""

    async def get_or_create_account(self, clerk_id: str, email: str) -> Optional[dict]:
        """Get account data by Clerk ID, creating user if not exists."""
        return await _get_or_create_user_by_clerk_id(clerk_id, email)

    async def update_profile(
        self,
        clerk_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> bool:
        """Update user profile fields by Clerk ID."""
        return await _update_user_profile_by_clerk_id(
            clerk_id=clerk_id,
            first_name=first_name,
            last_name=last_name,
            timezone=timezone,
            meeting_link=meeting_link,
        )
