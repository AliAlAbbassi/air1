from typing import Optional
from playwright._impl._api_structures import SetCookieParam
from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError
from .linkedin_profile import LinkedinProfile, CompanyPeople, ProfileExperience
from .profile_scraper import ProfileScraper
from .company_scraper import CompanyScraper
from .linkedin_outreach import LinkedinOutreach
from .navigation import navigate_to_linkedin_url
from .exceptions import ProfileScrapingError
from loguru import logger


class BrowserSession:
    def __init__(self, browser: Browser, linkedin_sid: Optional[str] = None):
        self.browser = browser
        self.linkedin_sid = linkedin_sid
        self.page = None

    async def _setup_page(self) -> Page:
        """Set up or reuse existing page with optional authentication cookies"""
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
            else:
                logger.debug("No LinkedIn session cookie provided - using unauthenticated mode")

        return self.page

    async def get_profile_info(self, profile_id: str) -> LinkedinProfile:
        """
        Get LinkedIn profile info from a profile ID.

        Args:
            profile_id: LinkedIn profile ID (e.g., 'john-doe-123')

        Returns:
            LinkedinProfile with extracted data, or empty LinkedinProfile on expected
            scraping failures (timeouts, missing elements, parse errors).

        Raises:
            ProfileScrapingError: On unexpected errors that may indicate bugs or
            significant issues requiring investigation.

        Note:
            AttributeError is caught as an expected error because Playwright locators
            can raise it when elements are detached from the DOM during scraping.
        """
        profile_url = f"https://www.linkedin.com/in/{profile_id}"
        page = await self._setup_page()
        await navigate_to_linkedin_url(page, profile_url)

        try:
            profile = await ProfileScraper.extract_profile_data(page)
            # Set username from the profile_id we navigated to
            profile.username = profile_id
            return profile
        except (PlaywrightTimeoutError, AttributeError, ValueError) as e:
            # Expected errors: timeouts, detached elements, parse failures
            logger.error(f"Failed to scrape profile {profile_id}: {str(e)}")
            return LinkedinProfile()
        except Exception as e:
            logger.error(f"Unexpected error scraping profile {profile_id}: {str(e)}")
            raise ProfileScrapingError(
                f"Unexpected error scraping profile {profile_id}: {str(e)}"
            ) from e

    async def get_profile_experience(self, profile_id: str) -> list[ProfileExperience]:
        """
        Get LinkedIn profile experience from a profile ID.

        Args:
            profile_id: LinkedIn profile ID (e.g., 'john-doe-123')

        Returns:
            List of ProfileExperience with extracted data, or empty list on expected
            scraping failures (timeouts, missing elements, parse errors).

        Note:
            This assumes the profile page is already loaded from get_profile_info.
        """
        if self.page is None:
            logger.error("Page not initialized. Call get_profile_info first.")
            return []

        try:
            return await ProfileScraper.extract_profile_experience(self.page)
        except (PlaywrightTimeoutError, AttributeError, ValueError) as e:
            logger.error(f"Failed to scrape experience for {profile_id}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping experience for {profile_id}: {str(e)}")
            return []

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
