from air1.services.outreach.repo import save_lead_complete, get_company_leads
from playwright.async_api import Playwright, async_playwright
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from loguru import logger

from air1.services.outreach.browser import BrowserSession
from air1.services.outreach.linkedin_profile import (
    LinkedinProfile,
    CompanyPeople,
    profile_to_lead,
    enrich_profile_with_username,
)
from air1.services.outreach.email import EmailTemplate, EmailResult

load_dotenv()


class IService(ABC):
    """
    Service interface for LinkedIn lead generation and email outreach
    """

    @abstractmethod
    async def scrape_company_leads(
        self, company_ids: list[str], limit=10, headless=True
    ) -> dict[str, int]:
        pass

    @abstractmethod
    async def send_outreach_emails(self, leads, template) -> List[EmailResult]:
        pass


class Service(IService):
    def __init__(self, playwright: Optional[Playwright] = None):
        self.playwright = playwright
        self._owns_playwright = False
        self._playwright_instance = None

        linkedin_sid = os.getenv("LINKEDIN_SID")
        if not linkedin_sid:
            raise ValueError("linkedin_sid environment variable is required")
        self.linkedin_sid = linkedin_sid

    async def __aenter__(self):
        if self.playwright is None:
            self._playwright_instance = async_playwright()
            self.playwright = await self._playwright_instance.__aenter__()
            self._owns_playwright = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_playwright and self._playwright_instance:
            await self._playwright_instance.__aexit__(exc_type, exc_val, exc_tb)

    async def launch_browser(self, headless=True) -> BrowserSession:
        if not self.playwright:
            raise RuntimeError(
                "Playwright not initialized. Use 'async with Service()' context manager."
            )
        browser = await self.playwright.chromium.launch(headless=headless)
        return BrowserSession(browser, self.linkedin_sid)

    async def get_profile_info(self, profile_id: str, headless=True) -> LinkedinProfile:
        """
        Get LinkedIn profile info from a profile ID (launches and closes browser automatically)

        Args:
            profile_id (str): LinkedIn profile ID (e.g., '')

        Returns:
            LinkedinProfile: Complete profile information
            :param profile_id:
            :param headless:
        """
        session = await self.launch_browser(headless=headless)
        try:
            return await session.get_profile_info(profile_id)
        finally:
            await session.browser.close()

    async def get_company_members(
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
        logger.info(f"Fetching Company Profiles for {company_id}...")
        session = await self.launch_browser(headless=headless)
        try:
            return await session.get_company_members(company_id, limit=limit)
        finally:
            await session.browser.close()

    async def scrape_and_save_company_leads(
        self, company_id: str, limit=10, headless=True
    ):
        """
        Scrape LinkedIn company profiles and save leads to database

        Args:
            company_id (str): LinkedIn company ID
            limit (int): Maximum number of profiles to process
            headless (bool): Run browser in headless mode

        Returns:
            int: Number of leads saved
        """
        logger.debug(f"Launching browser for {company_id}...")
        session = await self.launch_browser(headless=headless)
        leads_saved = 0

        try:
            logger.debug(f"Getting company members for {company_id}...")
            company_people = await session.get_company_members(company_id, limit=limit)
            logger.info(
                f"Found {len(company_people.profile_ids)} profiles for company {company_id}"
            )

            for profile_id in company_people.profile_ids:
                profile = await session.get_profile_info(profile_id)
                profile = enrich_profile_with_username(profile, profile_id)
                lead = profile_to_lead(profile)

                try:
                    success, lead_id = await save_lead_complete(
                        lead, profile, company_id, company_id
                    )
                    if success:
                        logger.success(
                            f"Saved lead: {lead.full_name} (ID: {lead_id}) for company {company_id}"
                        )
                        leads_saved += 1
                except Exception as e:
                    logger.error(f"Failed to save lead {lead.full_name}: {e}")

        finally:
            await session.browser.close()

        logger.info(f"Successfully saved {leads_saved} leads for company {company_id}")
        return leads_saved

    async def scrape_company_leads(
        self, company_ids: list[str], limit=10, headless=True
    ) -> dict[str, int]:
        """
        Args:
            company_ids: List of LinkedIn company IDs to scrape
            limit: Maximum number of company member pages
            headless: Run browser in headless mode

        Returns:
            dict: Results for each company with leads saved count
        """
        results = {}
        for company_id in company_ids:
            leads_saved = await self.scrape_and_save_company_leads(
                company_id, limit=limit, headless=headless
            )
            results[company_id] = leads_saved
        return results

    async def connect_with_linkedin_profiles(
        self,
        profile_usernames: list[str],
        message: Optional[str] = None,
        delay_between_connections: int = 5,
        headless: bool = True,
    ) -> dict[str, bool]:
        """
        Connect with multiple LinkedIn profiles (launches and closes browser automatically)

        Args:
            profile_usernames: List of LinkedIn profile usernames (e.g., ['john-doe-123', 'jane-smith-456'])
            message: Optional connection message to send with each request
            delay_between_connections: Delay in seconds between connections to avoid rate limits
            headless: Run browser in headless mode

        Returns:
            dict: Results for each username mapping to success status
        """
        logger.info(f"Starting LinkedIn outreach for {len(profile_usernames)} profiles")
        session = await self.launch_browser(headless=headless)

        try:
            return await session.connect_with_profiles(
                profile_usernames, message, delay_between_connections
            )
        finally:
            import time

            time.sleep(60)
            await session.browser.close()

    async def get_company_leads(self, company_name: str):
        return await get_company_leads(company_username=company_name)

    async def send_outreach_emails(self, leads, template) -> List[EmailResult]:
        """Send outreach emails to leads using template"""
        from air1.services.outreach.email import send_outreach_emails_to_leads

        return await send_outreach_emails_to_leads(leads, template)
