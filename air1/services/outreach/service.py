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
from air1.services.outreach.linkedin_api import LinkedInAPI
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
from air1.services.outreach.templates import DEFAULT_COLD_CONNECTION_NOTE

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

    @abstractmethod
    def research_prospect(
        self,
        linkedin_username: str,
        full_name: str | None = None,
        headline: str | None = None,
        company_name: str | None = None,
        icp_profile: any = None,
    ) -> any:
        """
        Research a prospect and generate AI summary with ICP scoring.

        Args:
            linkedin_username: LinkedIn username to research
            full_name: Prospect's full name
            headline: LinkedIn headline
            company_name: Current company
            icp_profile: ICPProfile to score against
        """
        pass

    @abstractmethod
    def generate_outreach_message(
        self,
        prospect_name: str,
        prospect_title: str | None = None,
        prospect_company: str | None = None,
        prospect_summary: str | None = None,
        company_summary: str | None = None,
        pain_points: list[str] | None = None,
        talking_points: list[str] | None = None,
        outreach_trigger: str | None = None,
        message_type: str = "linkedin_dm",
        voice_profile: any = None,
        outreach_rules: any = None,
    ) -> any:
        """
        Generate a personalized outreach message in the user's voice.

        Args:
            prospect_name: Name of the prospect
            prospect_title: Job title
            prospect_company: Company name
            prospect_summary: AI summary of the prospect
            company_summary: AI summary of the company
            pain_points: Identified pain points
            talking_points: Suggested talking points
            outreach_trigger: What triggered this outreach
            message_type: Type of message (connection_request, linkedin_dm, email, etc.)
            voice_profile: VoiceProfile for style cloning
            outreach_rules: OutreachRules with dos/don'ts
        """
        pass

    @abstractmethod
    def send_connection_request(
        self,
        profile_username: str,
        message_note: Optional[str] = None,
    ) -> bool:
        """
        Send a LinkedIn connection request to a profile.

        Args:
            profile_username: LinkedIn profile username (e.g., 'john-doe-123')
            message_note: Optional connection message/note (defaults to DEFAULT_COLD_CONNECTION_NOTE)

        Returns:
            bool: True if connection request was sent successfully
        """
        pass

    @abstractmethod
    async def connect_with_company_members(
        self,
        company_usernames: list[str],
        keywords: list[str] | None = None,
        regions: list[str] | None = None,
        pages: int = 1,
        delay_range: tuple[float, float] = (2.0, 5.0),
    ) -> dict[str, int]:
        """
        Search for employees at companies and send connection requests.

        Args:
            company_usernames: List of LinkedIn company usernames (e.g., ['revolut', 'stripe'])
            keywords: Keywords to filter employees (e.g., ['recruiter', 'talent'])
            regions: LinkedIn geo region IDs to filter by
            pages: Number of search result pages to process per company
            delay_range: Min/max seconds to wait between requests (to avoid rate limiting)

        Returns:
            dict[str, int]: Mapping of company username to number of successful connection requests
        """
        pass


class Service(IService):
    def __init__(self, playwright: Optional[Playwright] = None):
        self.playwright = playwright
        self._owns_playwright = False
        self._playwright_instance = None

        linkedin_write_sid = os.getenv("LINKEDIN_WRITE_SID")
        linkedin_read_sid = os.getenv("LINKEDIN_READ_SID")
        if not linkedin_write_sid and not linkedin_read_sid:
            raise ValueError("linkedin_sid environment variable is required")
        self.linkedin_write_sid = linkedin_write_sid
        self.linkedin_read_sid = linkedin_read_sid

        # Initialize the LinkedIn API with the write session cookie
        self.api = LinkedInAPI(cookies={"li_at": self.linkedin_write_sid})

    async def __aenter__(self):
        if self.playwright is None:
            self._playwright_instance = async_playwright()
            self.playwright = await self._playwright_instance.__aenter__()
            self._owns_playwright = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_playwright and self._playwright_instance:
            await self._playwright_instance.__aexit__(exc_type, exc_val, exc_tb)

    async def launch_browser(self, headless=True, read=True) -> BrowserSession:
        if not self.playwright:
            raise RuntimeError(
                "Playwright not initialized. Use 'async with Service()' context manager."
            )
        browser = await self.playwright.chromium.launch(headless=headless)
        return BrowserSession(
            browser, self.linkedin_read_sid if read else self.linkedin_write_sid
        )

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
                logger.info(
                    f"Limiting to {len(profile_ids)} profiles (profile_limit={profile_limit})"
                )

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
                company_id,
                limit=limit,
                headless=headless,
                keywords=keywords,
                location_ids=location_ids,
                profile_limit=profile_limit,
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

    async def save_lead_from_api(
        self,
        profile_username: str,
        company_username: str | None = None,
        job_title: str | None = None,
    ) -> int | None:
        """
        Fetch a LinkedIn profile via API and save it as a new lead.

        This method uses the LinkedIn API (no browser/Playwright) to fetch profile data,
        then creates a lead with the associated LinkedIn profile.

        Args:
            profile_username: LinkedIn profile username (e.g., 'john-doe-123')
            company_username: Optional company username for company membership
            job_title: Optional job title at the company

        Returns:
            lead_id if successful, None otherwise
        """
        logger.info(f"Fetching and saving lead for profile via API: {profile_username}")

        # Fetch profile data via API
        api_profile = self.api.get_profile(profile_username)

        if not api_profile:
            logger.warning(f"Could not fetch profile data for {profile_username}")
            return None

        if not api_profile.first_name and not api_profile.last_name:
            logger.warning(f"Profile {profile_username} has no name data")
            return None

        # Convert API profile to the format expected by save_lead_complete
        profile = LinkedinProfile(
            first_name=api_profile.first_name,
            full_name=api_profile.name or f"{api_profile.first_name} {api_profile.last_name}".strip(),
            username=profile_username,
            location=api_profile.location,
            headline=api_profile.headline,
            about=api_profile.about,
        )

        lead = profile_to_lead(profile)

        try:
            success, lead_id = await save_lead_complete(
                lead,
                profile,
                company_username=company_username,
                job_title=job_title,
            )

            if success and lead_id:
                logger.success(
                    f"Saved lead from API {profile_username}: {lead.full_name} (ID: {lead_id})"
                )
                return lead_id
            else:
                logger.error(f"Failed to save lead for profile {profile_username}")
                return None

        except Exception as e:
            logger.error(f"Error saving lead from API {profile_username}: {e}")
            return None

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

    def research_prospect(
        self,
        linkedin_username: str,
        full_name: str | None = None,
        headline: str | None = None,
        company_name: str | None = None,
        icp_profile: any = None,
    ):
        """
        Research a prospect and generate AI summary with ICP scoring.

        Args:
            linkedin_username: LinkedIn username to research
            full_name: Prospect's full name
            headline: LinkedIn headline
            company_name: Current company
            icp_profile: ICPProfile to score against

        Returns:
            ResearchOutput with AI summary, pain points, talking points, ICP score
        """
        from air1.agents.research.crew import ResearchProspectCrew
        from air1.agents.research.models import ProspectInput

        prospect = ProspectInput(
            linkedin_username=linkedin_username,
            full_name=full_name,
            headline=headline,
            company_name=company_name,
        )
        crew = ResearchProspectCrew(icp_profile=icp_profile)
        return crew.research_prospect(prospect)

    def generate_outreach_message(
        self,
        prospect_name: str,
        prospect_title: str | None = None,
        prospect_company: str | None = None,
        prospect_summary: str | None = None,
        company_summary: str | None = None,
        pain_points: list[str] | None = None,
        talking_points: list[str] | None = None,
        outreach_trigger: str | None = None,
        message_type: str = "linkedin_dm",
        voice_profile: any = None,
        outreach_rules: any = None,
    ):
        """
        Generate a personalized outreach message in the user's voice.

        Args:
            prospect_name: Name of the prospect
            prospect_title: Job title
            prospect_company: Company name
            prospect_summary: AI summary of the prospect
            company_summary: AI summary of the company
            pain_points: Identified pain points
            talking_points: Suggested talking points
            outreach_trigger: What triggered this outreach
            message_type: Type of message (connection_request, linkedin_dm, email, etc.)
            voice_profile: VoiceProfile for style cloning
            outreach_rules: OutreachRules with dos/don'ts

        Returns:
            GeneratedMessage with the message and metadata
        """
        from air1.agents.outreach.crew import OutreachMessageCrew
        from air1.agents.outreach.models import MessageRequest, MessageType

        # Map string to MessageType enum
        type_map = {
            "connection_request": MessageType.CONNECTION_REQUEST,
            "linkedin_dm": MessageType.LINKEDIN_DM,
            "inmail": MessageType.INMAIL,
            "follow_up": MessageType.FOLLOW_UP,
            "email": MessageType.EMAIL,
        }
        msg_type = type_map.get(message_type, MessageType.LINKEDIN_DM)

        request = MessageRequest(
            message_type=msg_type,
            prospect_name=prospect_name,
            prospect_title=prospect_title or "",
            prospect_company=prospect_company or "",
            prospect_summary=prospect_summary or "",
            company_summary=company_summary or "",
            pain_points=pain_points or [],
            talking_points=talking_points or [],
            outreach_trigger=outreach_trigger or "",
        )

        crew = OutreachMessageCrew(
            voice_profile=voice_profile,
            outreach_rules=outreach_rules,
        )
        return crew.generate_message(request)

    def send_connection_request(
        self,
        profile_username: str,
        message_note: Optional[str] = DEFAULT_COLD_CONNECTION_NOTE.strip(),
    ) -> bool:
        """
        Send a LinkedIn connection request to a profile.

        Args:
            profile_username: LinkedIn profile username (e.g., 'john-doe-123')
            message_note: Optional connection message/note (defaults to DEFAULT_COLD_CONNECTION_NOTE)

        Returns:
            bool: True if connection request was sent successfully
        """
        # Resolve the username to an fsd_profile URN
        logger.info(f"Resolving profile URN for username: {profile_username}")
        urn, tracking_id = self.api.get_profile_urn(profile_username)

        if not urn:
            logger.error(f"Could not resolve URN for username: {profile_username}")
            return False

        if not urn.startswith("urn:li:fsd_profile:"):
            logger.error(f"Expected fsd_profile URN, got: {urn}")
            return False

        logger.info(f"Resolved {profile_username} to URN: {urn}")

        # Send the connection request
        success = self.api.send_connection_request(
            profile_urn_id=urn,
            message=message_note,
            tracking_id=tracking_id,
        )

        if success:
            logger.success(f"Connection request sent to {profile_username}")
        else:
            logger.error(f"Failed to send connection request to {profile_username}")

        return success

    def get_company_members_from_api(self, company_username: str, keywords: list[str]):
        self.api.search_company_employees(
            company=company_username, keywords=keywords, regions=[]
        )

    async def get_profiles_for_outreach(self, limit: int = 50) -> list[dict]:
        """
        Get saved profiles that haven't been contacted yet.

        Args:
            limit: Maximum number of profiles to return

        Returns:
            List of profile dicts with username, lead_id, name, headline
        """
        from air1.db.prisma_client import get_prisma
        from air1.services.outreach.contact_point import has_linkedin_connection

        prisma = await get_prisma()

        profiles = await prisma.linkedinprofile.find_many(
            take=limit * 2,  # Fetch extra since some will be filtered
            order={"createdOn": "desc"},
            include={"lead": True},
        )

        result = []
        for p in profiles:
            if len(result) >= limit:
                break

            # Skip if already connected
            already_connected = await has_linkedin_connection(p.username)
            if already_connected:
                continue

            result.append({
                "username": p.username,
                "lead_id": p.leadId,
                "name": p.lead.fullName if p.lead else None,
                "headline": p.headline,
            })

        return result

    async def get_all_saved_profiles(self, limit: int = 50) -> list[dict]:
        """
        Get all saved profiles with their connection status.

        Args:
            limit: Maximum number of profiles to return

        Returns:
            List of profile dicts with username, lead_id, name, headline, is_connected
        """
        from air1.db.prisma_client import get_prisma
        from air1.services.outreach.contact_point import has_linkedin_connection

        prisma = await get_prisma()

        profiles = await prisma.linkedinprofile.find_many(
            take=limit,
            order={"createdOn": "desc"},
            include={"lead": True},
        )

        result = []
        for p in profiles:
            is_connected = await has_linkedin_connection(p.username)
            result.append({
                "username": p.username,
                "lead_id": p.leadId,
                "name": p.lead.fullName if p.lead else None,
                "headline": p.headline,
                "is_connected": is_connected,
            })

        return result

    async def profile_exists(self, username: str) -> bool:
        """Check if a LinkedIn profile already exists in the database."""
        profile = await get_linkedin_profile_by_username(username)
        return profile is not None

    async def has_connection_request(self, username: str) -> bool:
        """Check if we've already sent a connection request to this profile."""
        from air1.services.outreach.contact_point import has_linkedin_connection
        return await has_linkedin_connection(username)

    async def track_connection_request(self, lead_id: int) -> bool:
        """Track that a connection request was sent to a lead."""
        from air1.services.outreach.contact_point import insert_linkedin_connection
        return await insert_linkedin_connection(lead_id)

    async def connect_with_company_members(
        self,
        company_usernames: list[str],
        keywords: list[str] | None = None,
        regions: list[str] | None = None,
        pages: int = 1,
        delay_range: tuple[float, float] = (2.0, 5.0),
    ) -> dict[str, int]:
        """
        Search for employees at companies and send connection requests.

        Args:
            company_usernames: List of LinkedIn company usernames (e.g., ['revolut', 'stripe'])
            keywords: Keywords to filter employees (e.g., ['recruiter', 'talent'])
            regions: LinkedIn geo region IDs to filter by
            pages: Number of search result pages to process per company
            delay_range: Min/max seconds to wait between requests (to avoid rate limiting)

        Returns:
            dict[str, int]: Mapping of company username to number of successful connection requests
        """
        import random
        import time

        from air1.services.outreach.contact_point import insert_linkedin_connection
        from air1.services.outreach.repo import get_linkedin_profile_by_username

        results: dict[str, int] = {}

        for company_username in company_usernames:
            logger.info(f"Searching for employees at {company_username}...")

            employees = self.api.search_company_employees(
                company=company_username,
                keywords=keywords,
                regions=regions,
                pages=pages,
            )

            logger.info(f"Found {len(employees)} employees matching criteria for {company_username}")

            success_count = 0
            for i, employee in enumerate(employees):
                if not employee.public_id:
                    logger.warning(
                        f"[{company_username}][{i + 1}/{len(employees)}] Skipping employee without public_id"
                    )
                    continue

                username = employee.public_id
                logger.info(f"[{company_username}][{i + 1}/{len(employees)}] Sending request to {username}")

                success = self.send_connection_request(username)

                if success:
                    success_count += 1

                    # Track the connection
                    try:
                        linkedin_profile = await get_linkedin_profile_by_username(username)
                        lead_id = linkedin_profile.leadId if linkedin_profile else None

                        if not lead_id:
                            logger.info(
                                f"Lead not found for {username}, creating from LinkedIn API"
                            )
                            lead_id = await self.save_lead_from_api(
                                profile_username=username,
                                company_username=company_username,
                                job_title=employee.headline,
                            )

                        if lead_id:
                            await insert_linkedin_connection(lead_id)
                            logger.info(
                                f"Tracked connection for {username} (lead_id={lead_id})"
                            )
                        else:
                            logger.warning(f"Could not create lead for {username}")
                    except Exception as e:
                        logger.error(f"Failed to track connection for {username}: {e}")

                # Add random delay between requests to avoid rate limiting
                if i < len(employees) - 1:
                    delay = random.uniform(*delay_range)
                    logger.debug(f"Waiting {delay:.1f}s before next request...")
                    time.sleep(delay)

            logger.success(
                f"Completed {company_username}: {success_count}/{len(employees)} connection requests sent"
            )
            results[company_username] = success_count

        total = sum(results.values())
        logger.success(f"All companies completed: {total} total connection requests sent")
        return results

