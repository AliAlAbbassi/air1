"""
LinkedinOutreach: connects with people on linkedin.
Automated outreach, but done sequentially to emulate human behavior and avoid bot detection and rate limits.

Will include a faster option: fast_connect(). Don't care about it right now tho.
"""

from playwright.async_api import Page
from loguru import logger
import asyncio
from typing import Optional


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
            await page.goto(profile_url, timeout=30000, wait_until="domcontentloaded")
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
