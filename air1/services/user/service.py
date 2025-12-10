"""User service for account management."""

from abc import ABC, abstractmethod
from typing import Optional

from air1.services.user.account_repo import (
    get_account_by_user_id as _get_account_by_user_id,
    update_user_profile as _update_user_profile,
)


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
