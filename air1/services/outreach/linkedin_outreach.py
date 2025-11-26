"""
LinkedinOutreach: connects with people on linkedin.
Automated outreach, but done sequentially to emulate human behavior and avoid bot detection and rate limits.

Will include a faster option: fast_connect(). Don't care about it right now tho.
"""

import random
from typing import Optional

from loguru import logger
from playwright.async_api import Page

from .navigation import navigate_to_linkedin_url


class RateLimitHandler:
    """Handles LinkedIn rate limiting with exponential backoff and jitter"""

    def __init__(
        self,
        initial_delay: int = 5,
        max_delay: int = 300,
        max_retries: int = 5,
        jitter_factor: float = 0.3,
    ):
        """
        Initialize the rate limit handler.

        Args:
            initial_delay: Base delay in seconds between requests (default: 5)
            max_delay: Maximum delay in seconds during backoff (default: 300 / 5 min)
            max_retries: Maximum consecutive retries before giving up (default: 5)
            jitter_factor: Random variation factor (0.0-1.0) to avoid patterns (default: 0.3)
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.jitter_factor = jitter_factor
        self.current_delay = initial_delay
        self.consecutive_rate_limits = 0

    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to delay to avoid predictable patterns"""
        jitter_range = delay * self.jitter_factor
        # Ensure delay never goes below 1 second
        return max(1.0, delay + random.uniform(-jitter_range, jitter_range))

    async def detect_rate_limit(self, page: Page) -> bool:
        """
        Check if LinkedIn returned rate limit indicators.

        Looks for:
        - "Too many requests" messages
        - CAPTCHA challenges
        - Rate limit error pages
        - Unusual error states

        Args:
            page: Playwright page instance

        Returns:
            bool: True if rate limit detected, False otherwise
        """
        rate_limit_indicators = [
            # LinkedIn-specific rate limit text indicators
            'text="Too many requests"',
            'text="You\'ve reached the limit"',
            'text="You\'ve reached the weekly invitation limit"',
            'text="Please try again later"',
            # CAPTCHA indicators (LinkedIn uses specific challenge pages)
            'iframe[src*="captcha"]',
            'iframe[src*="challenge"]',
            '[data-test-id="captcha"]',
            'text="security verification"',
            'text="Let\'s do a quick security check"',
        ]

        for indicator in rate_limit_indicators:
            try:
                element = await page.query_selector(indicator)
                if element and await element.is_visible():
                    logger.warning(f"Rate limit indicator detected: {indicator}")
                    return True
            except Exception as e:
                # Selector might be invalid for some page states
                logger.debug(f"Selector check failed for '{indicator}': {e}")

        # Check page URL for error redirects
        current_url = page.url
        if any(
            error_path in current_url
            for error_path in ["/checkpoint/", "/error/", "/captcha/"]
        ):
            logger.warning(f"Rate limit redirect detected: {current_url}")
            return True

        return False

    async def wait_with_backoff(
        self, page: Page, detected_rate_limit: bool = False
    ) -> bool:
        """
        Wait with exponential backoff if rate limit is detected.

        Args:
            page: Playwright page instance
            detected_rate_limit: Whether a rate limit was detected

        Returns:
            bool: True if should continue, False if max retries exceeded
        """
        if detected_rate_limit:
            self.consecutive_rate_limits += 1

            if self.consecutive_rate_limits > self.max_retries:
                logger.error(
                    f"Max retries ({self.max_retries}) exceeded. Stopping to prevent account issues."
                )
                return False

            # Exponential backoff: double the delay each time
            self.current_delay = min(self.current_delay * 2, self.max_delay)
            delay_with_jitter = self._add_jitter(self.current_delay)

            logger.warning(
                f"Rate limit detected (attempt {self.consecutive_rate_limits}/{self.max_retries}). "
                f"Waiting {delay_with_jitter:.1f}s before retry"
            )
        else:
            # Reset on successful request
            self.consecutive_rate_limits = 0
            self.current_delay = self.initial_delay
            delay_with_jitter = self._add_jitter(self.current_delay)

            logger.debug(f"Waiting {delay_with_jitter:.1f}s before next request")

        await page.wait_for_timeout(int(delay_with_jitter * 1000))
        return True

    def reset(self) -> None:
        """Reset the handler to initial state"""
        self.current_delay = self.initial_delay
        self.consecutive_rate_limits = 0


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

            logger.info("Waiting for profile actions to load...")
            try:
                await page.wait_for_selector(
                    'button[id*="profile-overflow-action"]',
                    state="attached",
                    timeout=20000,
                )
                logger.info("More button loaded")
            except Exception as e:
                logger.warning(f"More button taking long to appear: {e}")

            # Get all More buttons and click the visible one
            more_buttons = await page.query_selector_all(
                'button[id*="profile-overflow-action"]'
            )

            more_button = None
            if more_buttons:
                logger.info(f"Found {len(more_buttons)} More button(s)")
                # Try to click the first visible one
                for btn in more_buttons:
                    if await btn.is_visible():
                        more_button = btn
                        break

                if not more_button and more_buttons:
                    # Just use the first one if none are marked visible
                    more_button = more_buttons[0]

            if more_button:
                await more_button.click()
                logger.info("Clicked More button to open dropdown")
                await page.wait_for_timeout(1000)
            else:
                logger.error("No More button found")
                return False

            # Get all Connect buttons and use the visible one
            connect_buttons = await page.query_selector_all(
                'div[aria-label*="Invite"][aria-label*="to connect"]'
            )

            connect_button = None
            if connect_buttons:
                logger.info(f"Found {len(connect_buttons)} Connect button(s)")
                # Use the first visible one
                for btn in connect_buttons:
                    if await btn.is_visible():
                        connect_button = btn
                        logger.info("Using visible Connect button")
                        break

                if not connect_button and connect_buttons:
                    # Just use the first one if none are marked visible
                    connect_button = connect_buttons[0]
                    logger.info("Using first Connect button")

            if not connect_button:
                logger.error(
                    f"Connect button not found in dropdown for {profile_username}"
                )
                return False

            # Try to click the connect button
            try:
                # First try normal click
                await connect_button.click()
            except Exception as e:
                logger.info(f"Normal click failed: {e}, trying force click")
                try:
                    await connect_button.click(force=True)
                except Exception as e2:
                    logger.info(
                        f"Force click also failed: {e2}, trying JavaScript click"
                    )
                    # Last resort - use JavaScript
                    await page.evaluate("(element) => element.click()", connect_button)

            logger.info(f"Clicked connect button for {profile_username}")
            await page.wait_for_timeout(2000)

            # Wait for connection modal to appear
            try:
                # Look for the modal that appears after clicking Connect
                modal_appeared = False
                modal_selectors = [
                    ".artdeco-modal",
                    '[role="dialog"]',
                    "div[data-test-modal]",
                ]

                for selector in modal_selectors:
                    modal = await page.query_selector(selector)
                    if modal and await modal.is_visible():
                        logger.info("Connection modal appeared")
                        modal_appeared = True
                        break

                if modal_appeared:
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

                    # Look for Send button
                    send_selectors = [
                        'button[aria-label*="Send now"]',
                        'button[aria-label*="Send invitation"]',
                        'button:has-text("Send")',
                        ".artdeco-modal button.artdeco-button--primary",
                    ]

                    send_button = None
                    for selector in send_selectors:
                        send_button = await page.query_selector(selector)
                        if send_button and await send_button.is_visible():
                            logger.info(f"Found send button with selector: {selector}")
                            break

                    if send_button:
                        await send_button.click()
                        logger.success(f"Connection request sent to {profile_username}")
                        await page.wait_for_timeout(2000)
                        return True
                    else:
                        logger.warning("No send button found in modal")
                        # Try pressing Enter as fallback
                        await page.keyboard.press("Enter")
                        logger.info(
                            f"Sent connection with Enter for {profile_username}"
                        )
                        await page.wait_for_timeout(2000)
                        return True
                else:
                    logger.warning(
                        "No connection modal appeared after clicking Connect"
                    )
                    return False

            except Exception as e:
                logger.error(f"Error handling connection modal: {e}")
                return False

        except Exception as e:
            logger.error(f"Error connecting to {profile_username}: {str(e)}")
            return False

    @staticmethod
    async def bulk_connect(
        page: Page,
        profile_usernames: list[str],
        message: Optional[str] = None,
        delay_between_connections: int = 5,
        max_delay: int = 300,
        max_retries: int = 5,
    ) -> dict[str, bool]:
        """
        Connect with multiple LinkedIn users sequentially with rate limit protection.

        Args:
            page: Playwright page instance with LinkedIn session
            profile_usernames: List of LinkedIn profile usernames
            message: Optional connection message for all users
            delay_between_connections: Base delay in seconds between connections (default: 5)
            max_delay: Maximum delay in seconds during backoff (default: 300 / 5 min)
            max_retries: Maximum consecutive retries before stopping (default: 5)

        Returns:
            dict: Results for each username (True if successful, False otherwise)
        """
        results = {}
        rate_limiter = RateLimitHandler(
            initial_delay=delay_between_connections,
            max_delay=max_delay,
            max_retries=max_retries,
        )

        logger.info(f"Starting bulk connect for {len(profile_usernames)} profiles")

        for i, username in enumerate(profile_usernames):
            logger.info(
                f"Connecting to profile {i + 1}/{len(profile_usernames)}: {username}"
            )

            success = await LinkedinOutreach.connect(page, username, message)
            results[username] = success

            if success:
                logger.success(f"✓ Connected to {username}")
            else:
                logger.warning(f"✗ Failed to connect to {username}")

            # Check for rate limiting after each connection attempt
            rate_limited = await rate_limiter.detect_rate_limit(page)

            if i < len(profile_usernames) - 1:
                should_continue = await rate_limiter.wait_with_backoff(
                    page, rate_limited
                )
                if not should_continue:
                    logger.error(
                        "Stopping bulk connect due to persistent rate limiting"
                    )
                    # Mark remaining profiles as not attempted
                    for remaining_username in profile_usernames[i + 1 :]:
                        results[remaining_username] = False
                    break

        successful_connections = sum(1 for success in results.values() if success)
        logger.info(
            f"Bulk connect completed: {successful_connections}/{len(profile_usernames)} successful connections"
        )

        return results
