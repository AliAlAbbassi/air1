import asyncio
import os
import random
from abc import ABC, abstractmethod
from typing import List, Optional

from dotenv import load_dotenv
from loguru import logger
from playwright.async_api import Playwright, async_playwright

from air1.services.outreach.browser import BrowserSession
from air1.services.outreach.email import EmailResult
from air1.services.outreach.linkedin_profile import (
    CompanyPeople,
    LinkedinProfile,
    get_current_company_info,
    profile_to_lead,
)
from air1.services.outreach.prisma_models import CompanyLeadRecord
from air1.services.outreach.repo import (
    get_company_leads,
    get_company_leads_by_headline,
    save_lead_complete,
)

load_dotenv()


class IService(ABC):
    """
    Service interface for LinkedIn lead generation and email outreach
    """

    @abstractmethod
    async def scrape_company_leads(
        self,
        company_ids: list[str],
        limit=10,
        headless=True,
        keywords: Optional[List[str]] = None,
        location_ids: Optional[List[str]] = None,
        profile_limit: Optional[int] = None,
    ) -> dict[str, int]:
        pass

    @abstractmethod
    async def send_outreach_emails(self, leads, template) -> List[EmailResult]:
        pass

    @abstractmethod
    async def get_company_leads_by_headline(
        self, company_username: str, search_term: str, limit: int = 10
    ) -> list[CompanyLeadRecord]:
        pass

    @abstractmethod
    async def connect_with_linkedin_profiles_tracked(
        self,
        username_lead_mapping: dict[str, int],
        message: Optional[str] = None,
        delay_between_connections: int = 5,
        headless: bool = True,
    ) -> dict[str, bool]:
        pass

    @abstractmethod
    async def save_lead_from_linkedin_profile(
        self, profile_username: str, headless: bool = True
    ) -> int | None:
        """
        Scrape a LinkedIn profile and save it as a new lead.

        This method scrapes the profile data and experience information,
        then creates a lead with the associated LinkedIn profile and company membership.

        Args:
            profile_username: LinkedIn profile username (e.g., 'john-doe-123')
            headless: Run browser in headless mode

        Returns:
            lead_id if successful, None otherwise
        """
        pass

    @abstractmethod
    async def create_onboarding_user(self, request) -> any:
        """Create a new user with all onboarding data."""
        pass

    @abstractmethod
    async def fetch_company_from_linkedin(self, linkedin_url: str) -> any:
        """Fetch company data from LinkedIn URL."""
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
        self,
        company_id: str,
        limit=10,
        headless=True,
        keywords: Optional[List[str]] = None,
        location_ids: Optional[List[str]] = None,
    ) -> CompanyPeople:
        """
        Get all profile IDs of people working at a company (launches and closes browser automatically)

        Args:
            company_id (str): LinkedIn company ID (e.g., 'oreyeon')
            limit (int): Maximum number of pages to load
            headless (bool): Run browser in headless mode
            keywords (List[str], optional): Keywords to filter members by headline
            location_ids (List[str], optional): LinkedIn geo region IDs to filter by location

        Returns:
            CompanyPeople: Set of profile IDs
        """
        logger.info(f"Fetching Company Profiles for {company_id}...")
        if keywords:
            logger.info(f"Filtering by keywords: {keywords}")
        if location_ids:
            logger.info(f"Filtering by location IDs: {location_ids}")
        session = await self.launch_browser(headless=headless)
        try:
            return await session.get_company_members(
                company_id, limit=limit, keywords=keywords, location_ids=location_ids
            )
        finally:
            await session.browser.close()

    async def scrape_and_save_company_leads(
        self,
        company_id: str,
        limit=10,
        headless=True,
        keywords: Optional[List[str]] = None,
        location_ids: Optional[List[str]] = None,
        profile_limit: Optional[int] = None,
    ):
        """
        Scrape LinkedIn company profiles and save leads to database

        Args:
            company_id (str): LinkedIn company ID
            limit (int): Maximum number of "Show more" clicks for pagination
            headless (bool): Run browser in headless mode
            keywords (List[str], optional): Keywords to filter members by headline
            location_ids (List[str], optional): LinkedIn geo region IDs to filter by location
            profile_limit (int, optional): Maximum number of profiles to process/save

        Returns:
            int: Number of leads saved
        """
        logger.debug(f"Launching browser for {company_id}...")
        if keywords:
            logger.debug(f"Using keywords filter: {keywords}")
        if location_ids:
            logger.debug(f"Using location filter: {location_ids}")
        session = await self.launch_browser(headless=headless)
        leads_saved = 0

        try:
            logger.debug(f"Getting company members for {company_id}...")
            company_people = await session.get_company_members(
                company_id, limit=limit, keywords=keywords, location_ids=location_ids
            )
            logger.info(
                f"Found {len(company_people.profile_ids)} profiles for company {company_id}"
            )

            profile_ids = list(company_people.profile_ids)
            if profile_limit is not None:
                profile_ids = profile_ids[:profile_limit]
                logger.info(f"Limiting to {len(profile_ids)} profiles (profile_limit={profile_limit})")

            for i, profile_id in enumerate(profile_ids):
                # Random delay between profiles to emulate human behavior (5-15 seconds)
                if i > 0:
                    delay = random.uniform(5, 15)
                    logger.debug(f"Waiting {delay:.1f}s before next profile...")
                    await asyncio.sleep(delay)

                profile = await session.get_profile_info(profile_id)
                lead = profile_to_lead(profile)

                # Extract experience to find the title at this specific company
                experiences = await session.get_profile_experience(profile_id)
                job_title = None
                for exp in experiences:
                    if exp.company_id == company_id:
                        job_title = exp.title
                        logger.debug(
                            f"Found matching experience for {profile_id} at {company_id}: {job_title}"
                        )
                        break

                # Fall back to headline if we couldn't find a matching experience
                if not job_title:
                    job_title = profile.headline
                    logger.debug(
                        f"No matching experience found for {profile_id} at {company_id}, using headline: {job_title}"
                    )

                success, lead_id = await save_lead_complete(
                    lead,
                    profile,
                    company_username=company_id,
                    job_title=job_title,
                )
                if success:
                    logger.success(
                        f"Saved lead: {lead.full_name} (ID: {lead_id}) for company {company_id}"
                    )
                    leads_saved += 1
                else:
                    logger.error(
                        f"Failed to save lead {lead.full_name} - stopping workflow due to DB error"
                    )
                    break

        finally:
            await session.browser.close()

        logger.info(f"Successfully saved {leads_saved} leads for company {company_id}")
        return leads_saved

    async def scrape_company_leads(
        self,
        company_ids: list[str],
        limit=10,
        headless=True,
        keywords: Optional[List[str]] = None,
        location_ids: Optional[List[str]] = None,
        profile_limit: Optional[int] = None,
    ) -> dict[str, int]:
        """
        Args:
            company_ids: List of LinkedIn company IDs to scrape
            limit: Maximum number of "Show more" clicks for pagination
            headless: Run browser in headless mode
            keywords: Optional list of keywords to filter members by headline
            location_ids: Optional list of LinkedIn geo region IDs to filter by location
            profile_limit: Maximum number of profiles to process/save per company

        Returns:
            dict: Results for each company with leads saved count
        """
        results = {}
        for company_id in company_ids:
            leads_saved = await self.scrape_and_save_company_leads(
                company_id, limit=limit, headless=headless, keywords=keywords, location_ids=location_ids, profile_limit=profile_limit
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
            await session.browser.close()

    async def get_company_leads(self, company_name: str):
        return await get_company_leads(company_username=company_name)

    async def send_outreach_emails(self, leads, template) -> List[EmailResult]:
        """Send outreach emails to leads using template"""
        from air1.services.outreach.email import send_outreach_emails_to_leads

        return await send_outreach_emails_to_leads(leads, template)

    async def get_company_leads_by_headline(
        self, company_username: str, search_term: str, limit: int = 10
    ) -> list[CompanyLeadRecord]:
        return await get_company_leads_by_headline(company_username, search_term, limit)

    async def connect_with_linkedin_profiles_tracked(
        self,
        username_lead_mapping: dict[str, int],
        message: Optional[str] = None,
        delay_between_connections: int = 5,
        headless: bool = True,
    ) -> dict[str, bool]:
        """
        Connect with LinkedIn profiles and track successful connections.

        Args:
            username_lead_mapping: Dict mapping LinkedIn usernames to lead_ids
            message: Optional connection message to send with each request
            delay_between_connections: Delay in seconds between connections to avoid rate limits
            headless: Run browser in headless mode

        Returns:
            dict: Results for each username mapping to success status
        """
        from air1.services.outreach.contact_point import insert_linkedin_connection

        profile_usernames = list(username_lead_mapping.keys())

        results = await self.connect_with_linkedin_profiles(
            profile_usernames=profile_usernames,
            message=message,
            delay_between_connections=delay_between_connections,
            headless=headless,
        )

        for username, success in results.items():
            if success and username in username_lead_mapping:
                lead_id = username_lead_mapping[username]
                await insert_linkedin_connection(lead_id)

        return results

    async def save_lead_from_linkedin_profile(
        self, profile_username: str, headless: bool = True
    ) -> int | None:
        """
        Scrape a LinkedIn profile and save it as a new lead.

        This method scrapes the profile data and experience information,
        then creates a lead with the associated LinkedIn profile and company membership.

        Args:
            profile_username: LinkedIn profile username (e.g., 'john-doe-123')
            headless: Run browser in headless mode

        Returns:
            lead_id if successful, None otherwise
        """
        logger.info(f"Scraping and saving lead for profile: {profile_username}")
        session = await self.launch_browser(headless=headless)

        try:
            profile = await session.get_profile_info(profile_username)

            if not profile.full_name:
                logger.warning(f"Could not extract profile data for {profile_username}")
                return None

            company_username, job_title = get_current_company_info(profile)
            if company_username:
                logger.debug(
                    f"Found current company: {company_username}, title: {job_title}"
                )

            lead = profile_to_lead(profile)

            success, lead_id = await save_lead_complete(
                lead,
                profile,
                company_username=company_username,
                job_title=job_title,
            )

            if success and lead_id:
                logger.success(
                    f"Saved lead from profile {profile_username}: {lead.full_name} (ID: {lead_id})"
                )
                return lead_id
            else:
                logger.error(f"Failed to save lead for profile {profile_username}")
                return None

        except Exception as e:
            logger.error(f"Error saving lead from profile {profile_username}: {e}")
            return None
        finally:
            await session.browser.close()

    async def create_onboarding_user(self, request):
        """Create a new user with all onboarding data."""
        from air1.services.outreach.onboarding import create_onboarding_user

        return await create_onboarding_user(request)

    async def fetch_company_from_linkedin(self, linkedin_url: str):
        """Fetch company data from LinkedIn URL."""
        from air1.services.outreach.onboarding import fetch_company_from_linkedin

        session = await self.launch_browser(headless=True)
        try:
            return await fetch_company_from_linkedin(linkedin_url, session)
        finally:
            await session.browser.close()
