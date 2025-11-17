"""
Navigation utilities for LinkedIn browser automation
"""
from playwright.async_api import Page


async def navigate_to_linkedin_url(page: Page, url: str) -> None:
    """
    Navigate to a LinkedIn URL with proper error handling

    Args:
        page: Playwright page instance
        url: URL to navigate to

    Raises:
        Exception: With specific error messages for LinkedIn authentication issues
    """
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except Exception as e:
        error_str = str(e)
        if "ERR_TOO_MANY_REDIRECTS" in error_str:
            raise Exception(
                "LinkedIn authentication failed. Your session cookie may be expired. "
                "Please update the 'linkedin_sid' in your .env file with a fresh cookie value."
            )
        elif "Timeout" in error_str:
            raise Exception(
                f"Failed to load LinkedIn page: {url}\n"
                "This could be due to:\n"
                "1. Invalid or expired linkedin_sid cookie in your .env file\n"
                "2. LinkedIn blocking automated access\n"
                "3. Network connectivity issues\n"
                "Please verify your linkedin_sid cookie is valid and try again."
            )
        raise