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
    async def connect(
        page: Page, profile_username: str, message: Optional[str] = None
    ) -> bool:
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

            # Try multiple selectors for the More button - be more specific to profile actions
            more_selectors = [
                '.pvs-profile-actions__custom button:has-text("More")',
                '.pv-top-card-v2-ctas button:has-text("More")',
                'button[aria-label*="More actions"]',
                'button[id*="profile-overflow-action"]',
                '.artdeco-dropdown__trigger:has-text("More")',
            ]

            more_button = None
            for selector in more_selectors:
                more_button = await page.query_selector(selector)
                if more_button:
                    logger.info(f"Found More button with selector: {selector}")
                    break

            if not more_button:
                logger.warning(f"No More button found for {profile_username}")
                buttons = await page.query_selector_all("button")
                logger.info(f"Available buttons: {len(buttons)}")
                for i, btn in enumerate(buttons[:5]):
                    text = await btn.text_content()
                    logger.info(f"Button {i}: {text}")
                return False

            await more_button.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await more_button.click(force=True)
            logger.info(f"Clicked More button for {profile_username}")
            await page.wait_for_timeout(1000)

            dropdown_appeared = False
            dropdown_selectors = [
                ".artdeco-dropdown__content",
                '[role="menu"]',
                ".artdeco-dropdown--is-open",
                ".artdeco-dropdown__content--is-open",
            ]

            for dropdown_selector in dropdown_selectors:
                try:
                    await page.wait_for_selector(dropdown_selector, timeout=1000)
                    logger.info(f"Dropdown appeared with selector: {dropdown_selector}")
                    dropdown_appeared = True
                    break
                except Exception:
                    continue

            if not dropdown_appeared:
                logger.warning(f"Dropdown didn't appear for {profile_username}")
                all_dropdowns = await page.query_selector_all('[class*="dropdown"]')
                logger.info(
                    f"Found {len(all_dropdowns)} elements with 'dropdown' in class"
                )
                return False

            connect_button = await page.query_selector(
                '.artdeco-dropdown--is-open .artdeco-dropdown__item:has([data-test-icon="connect-medium"])'
            )

            if not connect_button:
                # Fallback - find visible dropdown items and get the connect one
                visible_items = await page.query_selector_all(
                    ".artdeco-dropdown--is-open .artdeco-dropdown__item"
                )
                for item in visible_items:
                    icon = await item.query_selector(
                        '[data-test-icon="connect-medium"]'
                    )
                    if icon:
                        connect_button = item
                        break

            if not connect_button:
                logger.warning(
                    f"No visible connect button found for {profile_username}"
                )
                return False

            logger.info("Found visible connect button")

            await connect_button.click(force=True)
            logger.info(f"Clicked connect button for {profile_username}")
            await page.wait_for_timeout(1000)

            if message:
                add_note_button = await page.query_selector(
                    'button:has-text("Add a note")'
                )
                if add_note_button:
                    await add_note_button.click()
                    await page.wait_for_timeout(1000)

                    message_textarea = await page.query_selector("textarea")
                    if message_textarea:
                        await message_textarea.fill(message)
                        logger.info(f"Added message for {profile_username}")

            send_button = await page.query_selector(
                'button[aria-label*="Send"], button:has-text("Send")'
            )
            if send_button:
                await send_button.click()
                logger.success(f"Connection request sent to {profile_username}")
                await page.wait_for_timeout(2000)
                return True
            else:
                await page.keyboard.press("Enter")
                logger.info(f"Sent connection with Enter for {profile_username}")
                await page.wait_for_timeout(2000)
                return True

        except Exception as e:
            logger.error(f"Error connecting to {profile_username}: {str(e)}")
            return False

    @staticmethod
    async def bulk_connect(
        page: Page,
        profile_usernames: list[str],
        message: Optional[str] = None,
        delay_between_connections: int = 5,
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
            logger.info(
                f"Connecting to profile {i+1}/{len(profile_usernames)}: {username}"
            )

            success = await LinkedinOutreach.connect(page, username, message)
            results[username] = success

            if success:
                logger.success(f"✓ Connected to {username}")
            else:
                logger.warning(f"✗ Failed to connect to {username}")

            if i < len(profile_usernames) - 1:
                logger.debug(
                    f"Waiting {delay_between_connections} seconds before next connection..."
                )
                await page.wait_for_timeout(delay_between_connections * 1000)

        successful_connections = sum(1 for success in results.values() if success)
        logger.info(
            f"Bulk connect completed: {successful_connections}/{len(profile_usernames)} successful connections"
        )

        return results
