"""
LinkedinOutreach: connects with people on linkedin.
Automated outreach, but done sequentially to emulate human behavior and avoid bot detection and rate limits.

Will include a faster option: fast_connect(). Don't care about it right now tho.
"""

from playwright.async_api import Page
from loguru import logger
from typing import Optional
from .navigation import navigate_to_linkedin_url


class LinkedinOutreach:

    @staticmethod
    async def connect(page: Page, profile_username: str, message: Optional[str] = None) -> bool:
        """
        Connect with a LinkedIn user by their profile username

        Args:
            page: Playwright page instance with LinkedIn session
            profile_username: LinkedIn profile username (e.g., 'john-doe-123')
            message: Optional connection message

        Returns:
            bool: True if connection request was sent successfully, False otherwise
        """
        try:
            profile_url = f"https://www.linkedin.com/in/{profile_username}"
            await navigate_to_linkedin_url(page, profile_url)
            await page.wait_for_timeout(2000)

            connect_button = page.locator('button:has-text("Connect"), button[aria-label*="Connect"], button[data-control-name="connect"]')

            if await connect_button.count() == 0:
                logger.warning(f"Connect button not found for {profile_username}. User may already be connected or profile is private.")
                return False

            await connect_button.first.click()
            await page.wait_for_timeout(1500)

            if message:
                add_note_button = page.locator('button:has-text("Add a note"), button[aria-label*="Add a note"]')
                if await add_note_button.count() > 0:
                    await add_note_button.click()
                    await page.wait_for_timeout(1000)

                    message_textarea = page.locator('textarea[name="message"], textarea[id*="custom-message"]')
                    if await message_textarea.count() > 0:
                        await message_textarea.fill(message)
                        await page.wait_for_timeout(500)

            send_button = page.locator('button:has-text("Send"), button[aria-label*="Send"], button[data-control-name="send"]')
            if await send_button.count() > 0:
                await send_button.click()
                await page.wait_for_timeout(2000)
                logger.success(f"Connection request sent to {profile_username}")
                return True
            else:
                logger.error(f"Send button not found for {profile_username}")
                return False

        except Exception as e:
            logger.error(f"Error connecting to {profile_username}: {str(e)}")
            return False

    @staticmethod
    async def bulk_connect(
        page: Page,
        profile_usernames: list[str],
        message: Optional[str] = None,
        delay_between_connections: int = 5
    ) -> dict[str, bool]:
        """
        Connect with multiple LinkedIn users sequentially

        Args:
            page: Playwright page instance with LinkedIn session
            profile_usernames: List of LinkedIn profile usernames
            message: Optional connection message for all users
            delay_between_connections: Delay in seconds between connections (default: 5)

        Returns:
            dict: Results for each username (True if successful, False otherwise)
        """
        results = {}

        logger.info(f"Starting bulk connect for {len(profile_usernames)} profiles")

        for i, username in enumerate(profile_usernames):
            logger.info(f"Connecting to profile {i+1}/{len(profile_usernames)}: {username}")

            success = await LinkedinOutreach.connect(page, username, message)
            results[username] = success

            if success:
                logger.success(f"✓ Connected to {username}")
            else:
                logger.warning(f"✗ Failed to connect to {username}")

            if i < len(profile_usernames) - 1:
                logger.debug(f"Waiting {delay_between_connections} seconds before next connection...")
                await page.wait_for_timeout(delay_between_connections * 1000)

        successful_connections = sum(1 for success in results.values() if success)
        logger.info(f"Bulk connect completed: {successful_connections}/{len(profile_usernames)} successful connections")

        return results
