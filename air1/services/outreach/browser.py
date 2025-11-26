from typing import Optional
from playwright._impl._api_structures import SetCookieParam
from playwright.async_api import Browser, Page
from .linkedin_profile import LinkedinProfile, CompanyPeople
from .profile_scraper import ProfileScraper
from .company_scraper import CompanyScraper
from .linkedin_outreach import LinkedinOutreach
from .navigation import navigate_to_linkedin_url
from loguru import logger


class LinkedInAuthenticator:
    """Handles LinkedIn authentication via cookies"""

    def __init__(self, linkedin_sid: Optional[str], domain: str = ".linkedin.com"):
        self.linkedin_sid = linkedin_sid
        self.domain = domain

    async def authenticate_page(self, page: Page) -> None:
        """Apply authentication cookies to a page"""
        if self.linkedin_sid and self.linkedin_sid.strip():
            cookies: SetCookieParam = {
                "name": "li_at",
                "value": self.linkedin_sid,
                "domain": self.domain,
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Lax",
            }
            await page.context.add_cookies([cookies])


class BrowserSession:
    """Manages browser page lifecycle and delegates to scrapers"""

    def __init__(self, browser: Browser, authenticator: LinkedInAuthenticator):
        self.browser = browser
        self.authenticator = authenticator
        self.page = None

    async def _setup_page(self) -> Page:
        """Set up or reuse existing page with authentication"""
        if self.page is None:
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(60000)
            await self.authenticator.authenticate_page(self.page)

        return self.page

    async def get_profile_info(self, profile_id: str) -> LinkedinProfile:
        """
        Get LinkedIn profile info from a profile ID

        Args:
            profile_id (str): LinkedIn profile ID (e.g., '')

        Returns:
            LinkedinProfile: Complete profile information
        """
        profile_url = f"https://www.linkedin.com/in/{profile_id}"
        page = await self._setup_page()
        await navigate_to_linkedin_url(page, profile_url)

        try:
            return await ProfileScraper.extract_profile_data(page)
        except Exception as e:
            logger.error(f"Error scraping profile {profile_id}: {str(e)}")
            return LinkedinProfile()

    async def get_company_members(self, company_id: str, limit=10, keywords: Optional[list[str]] = None) -> CompanyPeople:
        """
        Get all profile IDs of people working at a company

        Args:
            company_id (str): LinkedIn company ID (e.g., 'oreyeon')
            limit (int): Maximum number of pages to load
            keywords (list[str], optional): Keywords to filter members by headline

        Returns:
            CompanyPeople: Set of profile IDs
        """
        # Build URL with optional keywords parameter
        company_url = f"https://www.linkedin.com/company/{company_id}/people/"
        if keywords:
            # Join keywords with comma for LinkedIn's URL format
            keywords_param = ",".join(keywords)
            company_url = f"{company_url}?keywords={keywords_param}"

        page = await self._setup_page()
        await navigate_to_linkedin_url(page, company_url)

        return await CompanyScraper.extract_company_members(page, company_id, limit)

    async def connect_with_profiles(
        self,
        profile_usernames: list[str],
        message: Optional[str] = None,
        delay_between_connections: int = 5,
    ) -> dict[str, bool]:
        """
        Connect with multiple LinkedIn profiles using existing session

        Args:
            profile_usernames: List of LinkedIn profile usernames
            message: Optional connection message
            delay_between_connections: Delay in seconds between connections

        Returns:
            dict: Results for each username (True if successful, False otherwise)
        """
        page = await self._setup_page()

        return await LinkedinOutreach.bulk_connect(
            page, profile_usernames, message, delay_between_connections
        )
