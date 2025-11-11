from air1.services.linkedin.repo import (
    insert_lead,
    insert_linkedin_profile,
    insert_linkedin_company_member,
)
from playwright.async_api import Playwright, async_playwright
import os
from dotenv import load_dotenv
from typing import Optional, Protocol

from air1.services.linkedin.browser import BrowserSession
from air1.db.db import db
from air1.services.linkedin.linkedin_profile import LinkedinProfile, CompanyPeople, Lead

load_dotenv()


class LinkedinServiceProtocol(Protocol):
    """Interface for LinkedIn scraping service"""

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

    async def scrape_and_save_company_leads(
            self, company_id: str, limit=10, headless=True
    ):
        """
        Scrape LinkedIn company profiles and save leads to database
        """


class Service:
    def __init__(self, playwright: Optional[Playwright] = None):
        self.playwright = playwright
        self._owns_playwright = False
        self._playwright_instance = None

        self.linkedin_sid = os.getenv("linkedin_sid")
        if not self.linkedin_sid:
            raise ValueError("linkedin_sid environment variable is required")

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
            return session.get_profile_info(profile_id)
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
        print(f"Fetching Company Profiles for {company_id}...")
        session = await self.launch_browser(headless=headless)
        try:
            return session.get_company_members(company_id, limit=limit)
        finally:
            await session.browser.close()

    async def save_linkedin_lead(
            self,
            lead: Lead,
            linkedin_lead: LinkedinProfile,
            company_url: str = None,
            company_name: str = None,
    ):
        inserted, lead_id = await insert_lead(lead)
        if not inserted:
            raise Exception("Failed to insert lead")

        linkedin_profile_id = await insert_linkedin_profile(linkedin_lead, lead_id)
        if not linkedin_profile_id:
            raise Exception("Failed to insert LinkedIn profile")

        if company_url and linkedin_profile_id:
            try:
                await insert_linkedin_company_member(
                    linkedin_profile_id, company_url, company_name
                )
            except Exception as e:
                print(f"Warning: Failed to save company mapping: {e}")

        return lead_id

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
        print(f"Scraping and saving leads for company: {company_id}")
        await db.connect()

        session = await self.launch_browser(headless=headless)
        leads_saved = 0

        try:
            company_people = session.get_company_members(company_id, limit=limit)
            print(f"Found {len(company_people.profile_ids)} profiles")

            for profile_id in company_people.profile_ids:
                profile = session.get_profile_info(profile_id)

                lead = Lead(
                    first_name=profile.first_name,
                    full_name=profile.full_name,
                    email=profile.email,
                    phone_number=profile.phone_number,
                )

                if lead.email:
                    try:
                        company_url = f"https://www.linkedin.com/company/{company_id}/"
                        lead_id = await self.save_linkedin_lead(
                            lead, profile, company_url, company_id
                        )
                        print(
                            f"Saved lead: {lead.full_name} (ID: {lead_id}) for company {company_id}"
                        )
                        leads_saved += 1
                    except Exception as e:
                        print(f"Failed to save lead {lead.full_name}: {e}")

                if profile.isTalent():
                    print("talent")
                    print(profile)
                else:
                    print("not talent")
                    print(profile)

        finally:
            await session.browser.close()

        print(f"Successfully saved {leads_saved} leads")
        return leads_saved
