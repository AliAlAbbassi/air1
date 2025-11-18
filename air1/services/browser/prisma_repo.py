from typing import Optional
from prisma import Prisma
from prisma.models import Lead, LinkedinProfile, LinkedinCompanyMember
from air1.db.prisma_client import get_prisma
from air1.services.browser.linkedin_profile import Lead as LeadData, LinkedinProfile as LinkedinProfileData
from air1.services.browser.prisma_models import CompanyLeadRecord
from loguru import logger


async def insert_lead(lead: LeadData) -> tuple[bool, int | None]:
    """Insert a new lead using Prisma"""
    try:
        prisma = await get_prisma()
        created_lead = await prisma.lead.create(
            data={
                "firstName": lead.first_name,
                "fullName": lead.full_name,
                "email": lead.email,
                "phoneNumber": lead.phone_number,
            }
        )
        return True, created_lead.leadId
    except Exception as e:
        logger.error(f"Failed to insert lead: {e}")
        return False, None


async def insert_linkedin_profile(profile: LinkedinProfileData, lead_id: int) -> int | None:
    """Insert a LinkedIn profile using Prisma"""
    try:
        if not profile.username:
            logger.error("Username is required for LinkedIn profile insertion")
            return None

        logger.info(
            f"Inserting LinkedIn profile for lead_id={lead_id}, username={profile.username}"
        )

        prisma = await get_prisma()
        created_profile = await prisma.linkedinprofile.create(
            data={
                "leadId": lead_id,
                "username": profile.username,
                "location": profile.location,
                "headline": profile.headline,
                "about": profile.about,
            }
        )

        logger.info(
            f"LinkedIn profile insertion result: linkedin_profile_id={created_profile.linkedinProfileId}"
        )
        return created_profile.linkedinProfileId
    except Exception as e:
        logger.error(
            f"Failed to insert linkedin profile for lead_id={lead_id}, username={profile.username}: {e}"
        )
        return None


async def get_linkedin_profile_by_username(username: str) -> LinkedinProfile | None:
    """Fetch LinkedIn profile by username using Prisma"""
    try:
        prisma = await get_prisma()
        profile = await prisma.linkedinprofile.find_unique(
            where={"username": username}
        )
        return profile
    except Exception as e:
        logger.error(f"Failed to get LinkedIn profile for username {username}: {e}")
        return None


async def get_company_members_by_username(username: str) -> list[LinkedinCompanyMember]:
    """Fetch all company members by username using Prisma"""
    try:
        prisma = await get_prisma()
        members = await prisma.linkedincompanymember.find_many(
            where={"username": username}
        )
        return members
    except Exception as e:
        logger.error(f"Failed to get company members for username {username}: {e}")
        return []


async def get_company_member_by_profile_and_username(
    linkedin_profile_id: int, username: str
) -> LinkedinCompanyMember | None:
    """Fetch specific company member by profile ID and username using Prisma"""
    try:
        prisma = await get_prisma()
        member = await prisma.linkedincompanymember.find_first(
            where={
                "linkedinProfileId": linkedin_profile_id,
                "username": username,
            }
        )
        return member
    except Exception as e:
        logger.error(
            f"Failed to get company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )
        return None


async def insert_linkedin_company_member(
    linkedin_profile_id: int, username: str, title: str | None = None
):
    """Insert a LinkedIn company member using Prisma"""
    try:
        if not username:
            logger.error("Username is required for company member insertion")
            return None

        logger.info(
            f"Inserting company member for linkedin_profile_id={linkedin_profile_id}, username={username}, title={title}"
        )

        prisma = await get_prisma()
        await prisma.linkedincompanymember.create(
            data={
                "linkedinProfileId": linkedin_profile_id,
                "username": username,
                "title": title,
            }
        )

        logger.info(
            f"Company member insertion successful for linkedin_profile_id={linkedin_profile_id}, username={username}"
        )
    except Exception as e:
        logger.error(
            f"Failed to insert company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )


async def save_lead_complete(
    lead: LeadData,
    profile: LinkedinProfileData,
    username: str | None = None,
    title: str | None = None,
) -> tuple[bool, int | None]:
    """Save lead with profile and company association in one transaction using Prisma."""
    try:
        prisma = await get_prisma()

        async with prisma.tx() as transaction:
            # Insert lead
            created_lead = await transaction.lead.create(
                data={
                    "firstName": lead.first_name,
                    "fullName": lead.full_name,
                    "email": lead.email,
                    "phoneNumber": lead.phone_number,
                }
            )

            if not created_lead:
                return False, None

            # Insert LinkedIn profile
            created_profile = await transaction.linkedinprofile.create(
                data={
                    "leadId": created_lead.leadId,
                    "username": profile.username,
                    "location": profile.location,
                    "headline": profile.headline,
                    "about": profile.about,
                }
            )

            if not created_profile:
                return False, None

            # Insert company member if username provided
            if username and created_profile.linkedinProfileId:
                await transaction.linkedincompanymember.create(
                    data={
                        "linkedinProfileId": created_profile.linkedinProfileId,
                        "username": username,
                        "title": title,
                    }
                )

            return True, created_lead.leadId
    except Exception as e:
        logger.error(f"Failed to save lead complete: {e}")
        return False, None


async def get_company_leads_by_headline(company_username: str, search_term: str) -> list[CompanyLeadRecord]:
    """Get company leads by headline text using Prisma"""
    try:
        prisma = await get_prisma()

        # This query is more complex and might need raw SQL or multiple queries
        # For now, let's implement a basic version
        leads = await prisma.lead.find_many(
            include={
                "linkedinProfile": {
                    "include": {
                        "companyMemberships": True
                    }
                }
            }
        )

        # Filter based on company username and headline
        filtered_leads = []
        for lead in leads:
            if lead.linkedinProfile:
                profile = lead.linkedinProfile
                # Check if profile has company membership for the given company
                has_company_membership = any(
                    member.username == company_username
                    for member in profile.companyMemberships
                )

                # Check if headline contains search term
                headline_match = (
                    profile.headline and
                    search_term.lower() in profile.headline.lower()
                )

                if has_company_membership and headline_match:
                    # Create a CompanyLeadRecord
                    company_lead = CompanyLeadRecord(
                        lead_id=lead.leadId,
                        first_name=lead.firstName,
                        full_name=lead.fullName,
                        email=lead.email,
                        username=profile.username,
                        headline=profile.headline,
                        company_name=company_username,
                    )
                    filtered_leads.append(company_lead)

        return filtered_leads
    except Exception as e:
        logger.error(
            f"Failed to search company leads by headline for {company_username}: {e}"
        )
        return []


async def get_company_leads(company_username: str) -> list[CompanyLeadRecord]:
    """Get all leads for a company using Prisma"""
    try:
        prisma = await get_prisma()

        # Get all company members for this company
        company_members = await prisma.linkedincompanymember.find_many(
            where={"username": company_username},
            include={
                "linkedinProfile": {
                    "include": {
                        "lead": True
                    }
                }
            }
        )

        # Transform to match the expected format
        company_leads = []
        for member in company_members:
            if member.linkedinProfile and member.linkedinProfile.lead:
                profile = member.linkedinProfile
                lead = profile.lead

                company_lead = CompanyLeadRecord(
                    lead_id=lead.leadId,
                    first_name=lead.firstName,
                    full_name=lead.fullName,
                    email=lead.email,
                    username=profile.username,
                    headline=profile.headline,
                    company_name=company_username,
                )
                company_leads.append(company_lead)

        return company_leads
    except Exception as e:
        logger.error(f"Failed to get company leads for {company_username}: {e}")
        raise RuntimeError(
            f"Repo error retrieving company leads for '{company_username}': {str(e)}"
        ) from e