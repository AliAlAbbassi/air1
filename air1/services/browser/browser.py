from playwright._impl._api_structures import SetCookieParam
from playwright.async_api import Browser, Page
from .linkedin_profile import LinkedinProfile, CompanyPeople
from .profile_scraper import ProfileScraper
from .company_scraper import CompanyScraper
from .linkedin_outreach import LinkedinOutreach
from .navigation import navigate_to_linkedin_url
from loguru import logger
from typing import Optional


class BrowserSession:
    def __init__(self, browser: Browser, linkedin_sid: str):
        self.browser = browser
        self.linkedin_sid = linkedin_sid
        self.page = None

    async def _setup_page(self) -> Page:
        """Set up or reuse existing page with authentication cookies"""
        if self.page is None:
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(60000)

            if self.linkedin_sid:
                cookies: SetCookieParam = {
                    "name": "li_at",
                    "value": self.linkedin_sid,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
                await self.page.context.add_cookies([cookies])

        return self.page

    async def _navigate_to_url(self, url: str) -> None:
        """Navigate to a specific URL with error handling"""
        if not self.page:
            raise Exception("Page not initialized. Call _setup_page() first.")

        await navigate_to_linkedin_url(self.page, url)

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
        await self._navigate_to_url(profile_url)

        try:
            return await ProfileScraper.extract_profile_data(page)
        except Exception as e:
            logger.error(f"Error scraping profile {profile_id}: {str(e)}")
            return LinkedinProfile()

    async def get_company_members(self, company_id: str, limit=10) -> CompanyPeople:
        """
        Get all profile IDs of people working at a company

        Args:
            company_id (str): LinkedIn company ID (e.g., 'oreyeon')

        Returns:
            CompanyPeople: Set of profile IDs
        """
        company_url = f"https://www.linkedin.com/company/{company_id}/people/"
        page = await self._setup_page()
        await self._navigate_to_url(company_url)

        return await CompanyScraper.extract_company_members(page, company_id, limit)

    async def connect_with_profiles(
        self,
        profile_usernames: list[str],
        message: Optional[str] = None,
        delay_between_connections: int = 5
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
        if not self.page:
            await self._setup_page()

        return await LinkedinOutreach.bulk_connect(
            self.page, profile_usernames, message, delay_between_connections
        )
