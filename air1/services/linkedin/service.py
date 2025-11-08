from playwright.sync_api import Playwright, sync_playwright
import os
from dotenv import load_dotenv
from typing import Optional, Protocol

from air1.services.linkedin.browser import BrowserSession

from air1.services.linkedin.models import LinkedinProfile, CompanyPeople

load_dotenv()


class LinkedinServiceProtocol(Protocol):
    """Interface for LinkedIn scraping service"""

    def launch_browser(self, headless: bool = True) -> BrowserSession:
        """Launch a browser and return a session for scraping profiles"""
        ...

    def get_profile_info(
        self, profile_id: str, headless: bool = True
    ) -> LinkedinProfile:
        """Get LinkedIn profile info from a profile ID"""
        ...

    def get_company_members(
        self, company_id: str, limit=10, headless: bool = True
    ) -> CompanyPeople:
        """Get all profile IDs of people working at a company"""
        ...


class Service:
    def __init__(self, playwright: Optional[Playwright] = None):
        if playwright is None:
            self._playwright_instance = sync_playwright()
            self.playwright = self._playwright_instance.__enter__()
            self._owns_playwright = True
        else:
            self.playwright = playwright
            self._owns_playwright = False

        self.linkedin_sid = os.getenv("linkedin_sid")
        if not self.linkedin_sid:
            raise ValueError("linkedin_sid environment variable is required")

    def __del__(self):
        if hasattr(self, "_owns_playwright") and self._owns_playwright:
            self._playwright_instance.__exit__(None, None, None)

    def launch_browser(self, headless=True) -> BrowserSession:
        """Launch a browser and return a session for scraping profiles"""
        browser = self.playwright.chromium.launch(headless=headless)
        return BrowserSession(browser, self.linkedin_sid)

    def get_profile_info(self, profile_id: str, headless=True) -> LinkedinProfile:
        """
        Get LinkedIn profile info from a profile ID (launches and closes browser automatically)

        Args:
            profile_id (str): LinkedIn profile ID (e.g., '')

        Returns:
            LinkedinProfile: Complete profile information
            :param profile_id:
            :param headless:
        """
        session = self.launch_browser(headless=headless)
        try:
            return session.get_profile_info(profile_id)
        finally:
            session.browser.close()

    def get_company_members(
        self, company_id: str, limit=10, headless=True
    ) -> CompanyPeople:
        """
        Get all profile IDs of people working at a company (launches and closes browser automatically)

        Args:
            company_id (str): LinkedIn company ID (e.g., 'oreyeon')

        Returns:
            CompanyPeople: Set of profile IDs
            :param company_id:
            :param limit:
            :param headless:
        """
        print(f"Fetching Company Profiles for {company_id}...")
        session = self.launch_browser(headless=headless)
        try:
            return session.get_company_members(company_id, limit=limit)
        finally:
            session.browser.close()
