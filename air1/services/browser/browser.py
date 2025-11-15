from playwright._impl._api_structures import SetCookieParam
from playwright.async_api import Browser, Page
from .linkedin_profile import LinkedinProfile, CompanyPeople
from .profile_scraper import ProfileScraper
from .company_scraper import CompanyScraper
from loguru import logger


class BrowserSession:
    def __init__(self, browser: Browser, linkedin_sid: str):
        self.browser = browser
        self.linkedin_sid = linkedin_sid
        self.page = None

    async def _setup_page(self, url: str) -> Page:
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

        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
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
        page = await self._setup_page(profile_url)

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
        page = await self._setup_page(company_url)

        return await CompanyScraper.extract_company_members(page, company_id, limit)
