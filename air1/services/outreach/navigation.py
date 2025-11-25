"""
Navigation utilities for LinkedIn browser automation
"""
from playwright.async_api import Page
from loguru import logger


async def navigate_to_linkedin_url(page: Page, url: str) -> None:
    """
    Navigate to a LinkedIn URL with proper error handling

    Args:
        page: Playwright page instance (must be initialized)
        url: URL to navigate to

    Raises:
        Exception: With specific error messages for LinkedIn authentication issues
    """
    if not page:
        raise Exception("Page not initialized. Call setup page method first.")

    # First check current URL - if we're already on the right page, no need to navigate
    current_url = page.url
    if url in current_url:
        logger.info(f"Already on target page: {current_url}")
        return

    logger.info(f"Navigating to: {url}")

    # Simple navigation - just start loading
    try:
        await page.goto(url, wait_until="commit", timeout=15000)
    except Exception as e:
        # Check if we made it to the page anyway
        current_url = page.url
        if "/in/" in url and "/in/" in current_url:
            logger.info("On profile page")
        else:
            logger.error(f"Navigation failed: {str(e)}")

    # Don't wait here - let the calling code wait for specific elements

    # Check for login redirect
    final_url = page.url
    if "linkedin.com/login" in final_url or "linkedin.com/checkpoint" in final_url:
        raise Exception(
            "Redirected to LinkedIn login page. Your session cookie may be expired. "
            "Please update the 'linkedin_sid' in your .env file with a fresh cookie value."
        )