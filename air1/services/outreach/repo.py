"""Repository functions for outreach data persistence.

API Contract for Error Handling:
--------------------------------
All functions in this module follow a consistent error handling pattern:

1. **Database errors (PrismaError)**: These are expected operational failures
   (connection issues, constraint violations, etc.). Functions return a failure
   indicator (False, None, or empty list) and log at ERROR level. Callers should
   check return values.

2. **Unexpected errors**: Any non-database exception indicates a potential bug or
   infrastructure issue. Functions raise domain-specific exceptions (LeadInsertionError,
   ProfileInsertionError, QueryError) wrapping the original error. Callers should
   let these propagate for investigation.

Return Value Conventions:
- Insert functions: Return (bool, id|None) or id|None - check for None/False
- Query functions: Return object|None or list - check for None or empty list
- All functions: Raise on unexpected errors
"""

from loguru import logger
from prisma.errors import PrismaError
from prisma.models import LinkedinCompanyMember, LinkedinProfile

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import outreach_queries as queries
from air1.services.outreach.exceptions import (
    LeadInsertionError,
    ProfileInsertionError,
    QueryError,
)
from air1.services.outreach.linkedin_profile import (
    Lead as LeadData,
)
from air1.services.outreach.linkedin_profile import (
    LinkedinProfile as LinkedinProfileData,
)
from air1.services.outreach.prisma_models import CompanyLeadRecord


async def insert_lead(lead: LeadData) -> tuple[bool, int | None]:
    try:
        prisma = await get_prisma()

        result = await queries.insert_lead(
            prisma,
            first_name=lead.first_name,
            full_name=lead.full_name,
            email=lead.email,
            phone_number=lead.phone_number,
        )

        if result:
            return True, result["leadId"]
        return False, None
    except PrismaError as e:
        logger.error(f"Database error inserting lead: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error inserting lead: {e}")
        raise LeadInsertionError(f"Unexpected error inserting lead: {e}") from e


async def insert_linkedin_profile(
    profile: LinkedinProfileData, lead_id: int
) -> int | None:
    try:
        if not profile.username:
            logger.error("Username is required for LinkedIn profile insertion")
            return None

        logger.info(
            f"Inserting LinkedIn profile for lead_id={lead_id}, username={profile.username}"
        )

        prisma = await get_prisma()
        result = await queries.insert_linkedin_profile(
            prisma,
            lead_id=int(lead_id),
            username=profile.username,
            location=profile.location,
            headline=profile.headline,
            about=profile.about,
        )

        if result:
            profile_id = result["linkedinProfileId"]
            logger.info(
                f"LinkedIn profile insertion result: linkedin_profile_id={profile_id}"
            )
            return profile_id
        return None
    except PrismaError as e:
        logger.error(
            f"Database error inserting linkedin profile for lead_id={lead_id}, username={profile.username}: {e}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error inserting linkedin profile for lead_id={lead_id}, username={profile.username}: {e}"
        )
        raise ProfileInsertionError(
            f"Unexpected error inserting linkedin profile for lead_id={lead_id}: {e}"
        ) from e


async def get_linkedin_profile_by_username(username: str) -> LinkedinProfile | None:
    try:
        prisma = await get_prisma()
        result = await queries.get_linkedin_profile_by_username(
            prisma, username=username
        )

        if result:
            return LinkedinProfile(**result)
        return None
    except PrismaError as e:
        logger.error(
            f"Database error getting LinkedIn profile for username {username}: {e}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error getting LinkedIn profile for username {username}: {e}"
        )
        raise QueryError(
            f"Unexpected error getting LinkedIn profile for username {username}: {e}"
        ) from e


async def get_company_members_by_username(username: str) -> list[LinkedinCompanyMember]:
    try:
        prisma = await get_prisma()
        results = await queries.get_company_members_by_username(
            prisma, username=username
        )

        return [LinkedinCompanyMember(**row) for row in results]
    except PrismaError as e:
        logger.error(
            f"Database error getting company members for username {username}: {e}"
        )
        return []
    except Exception as e:
        logger.error(
            f"Unexpected error getting company members for username {username}: {e}"
        )
        raise QueryError(
            f"Unexpected error getting company members for username {username}: {e}"
        ) from e


async def get_company_member_by_profile_and_username(
    linkedin_profile_id: int, username: str
) -> LinkedinCompanyMember | None:
    try:
        prisma = await get_prisma()
        result = await queries.get_company_member_by_profile_and_username(
            prisma, linkedin_profile_id=linkedin_profile_id, username=username
        )

        if result:
            return LinkedinCompanyMember(**result)
        return None
    except PrismaError as e:
        logger.error(
            f"Database error getting company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error getting company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )
        raise QueryError(
            f"Unexpected error getting company member for linkedin_profile_id={linkedin_profile_id}: {e}"
        ) from e


async def insert_linkedin_company_member(
    linkedin_profile_id: int, username: str, title: str | None = None
):
    try:
        if not username:
            logger.error("Username is required for company member insertion")
            return None

        logger.info(
            f"Inserting company member for linkedin_profile_id={linkedin_profile_id}, username={username}, title={title}"
        )

        prisma = await get_prisma()
        await queries.insert_linkedin_company_member(
            prisma,
            linkedin_profile_id=linkedin_profile_id,
            username=username,
            title=title,
        )

        logger.info(
            f"Company member insertion successful for linkedin_profile_id={linkedin_profile_id}, username={username}"
        )
    except PrismaError as e:
        logger.error(
            f"Database error inserting company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error inserting company member for linkedin_profile_id={linkedin_profile_id}, username={username}: {e}"
        )
        raise QueryError(
            f"Unexpected error inserting company member for linkedin_profile_id={linkedin_profile_id}: {e}"
        ) from e


async def save_lead_complete(
    lead: LeadData,
    profile: LinkedinProfileData,
    company_username: str | None = None,
    job_title: str | None = None,
) -> tuple[bool, int | None]:
    """
    Save a complete lead with profile and optional company association.

    Args:
        lead: Lead information (name, email, phone)
        profile: LinkedIn profile information
        company_username: The company's LinkedIn username (e.g., 'google')
        job_title: The person's job title at the company

    Returns:
        Tuple of (success: bool, lead_id: int | None)
    """
    try:
        prisma = await get_prisma()

        async with prisma.tx() as transaction:
            # Insert lead using aiosql
            lead_result = await queries.insert_lead(
                transaction,
                first_name=lead.first_name,
                full_name=lead.full_name,
                email=lead.email,
                phone_number=lead.phone_number,
            )

            if not lead_result:
                return False, None

            lead_id = lead_result["leadId"]

            # Insert LinkedIn profile using aiosql
            profile_result = await queries.insert_linkedin_profile(
                transaction,
                lead_id=int(lead_id),
                username=profile.username,
                location=profile.location,
                headline=profile.headline,
                about=profile.about,
            )

            if not profile_result:
                return False, None

            profile_id = profile_result["linkedinProfileId"]

            # Insert company member if company_username provided
            if company_username:
                await queries.insert_linkedin_company_member(
                    transaction,
                    linkedin_profile_id=profile_id,
                    username=company_username,
                    title=job_title,
                )

            return True, lead_id
    except PrismaError as e:
        logger.error(f"Database error saving lead complete: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error saving lead complete: {e}")
        raise LeadInsertionError(f"Unexpected error saving lead complete: {e}") from e


async def get_company_leads_by_headline(
    company_username: str, search_term: str, limit: int = 10
) -> list[CompanyLeadRecord]:
    """Get company leads by headline text using raw SQL (complex join query)"""
    try:
        prisma = await get_prisma()

        results = await queries.get_company_leads_by_headline(
            prisma,
            company_username=company_username,
            search_term=search_term,
            limit=limit,
        )

        return [CompanyLeadRecord(**row) for row in results]
    except PrismaError as e:
        logger.error(
            f"Database error getting company leads by headline for {company_username}: {e}"
        )
        return []
    except Exception as e:
        logger.error(
            f"Unexpected error getting company leads by headline for {company_username}: {e}"
        )
        raise QueryError(
            f"Unexpected error getting company leads by headline for {company_username}: {e}"
        ) from e


async def get_company_leads(company_username: str) -> list[CompanyLeadRecord]:
    """Get all leads for a company using raw SQL (complex join query)"""
    try:
        prisma = await get_prisma()

        results = await queries.get_company_leads(
            prisma, company_username=company_username
        )

        return [CompanyLeadRecord(**row) for row in results]
    except PrismaError as e:
        logger.error(
            f"Database error getting company leads for {company_username}: {e}"
        )
        raise QueryError(
            f"Database error retrieving company leads for '{company_username}': {str(e)}"
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error getting company leads for {company_username}: {e}"
        )
        raise QueryError(
            f"Unexpected error retrieving company leads for '{company_username}': {str(e)}"
        ) from e


async def insert_contact_point(lead_id: int, contact_point_type_id: int) -> bool:
    try:
        logger.debug(
            f"Attempting to insert contact point for lead_id={lead_id}, type_id={contact_point_type_id}"
        )
        prisma = await get_prisma()
        result = await queries.insert_contact_point(
            prisma,
            lead_id=lead_id,
            contact_point_type_id=contact_point_type_id,
        )

        if result and result.get("contact_point_id"):
            logger.info(
                f"Contact point inserted successfully: id={result['contact_point_id']}, lead_id={lead_id}, type_id={contact_point_type_id}"
            )
            return True
        else:
            logger.error(
                f"Insert contact point returned no result for lead_id={lead_id}"
            )
            return False
    except PrismaError as e:
        logger.error(
            f"Database error inserting contact point for lead_id={lead_id}: {e}",
            exc_info=True,
        )
        raise QueryError(
            f"Database error inserting contact point for lead_id={lead_id}: {e}"
        ) from e
    except Exception as e:
        logger.error(
            f"Failed to insert contact point for lead_id={lead_id}: {e}", exc_info=True
        )
        return False


# ============================================================================
# COMPANY FUNCTIONS
# ============================================================================


async def save_company(
    name: str,
    linkedin_username: str | None = None,
    source: str | None = None,
    job_geo_id: str | None = None,
) -> int | None:
    """
    Save a company to the database.

    Args:
        name: Company name
        linkedin_username: LinkedIn company username (e.g., 'revolut')
        source: Source of the company (e.g., 'job_search', 'manual')
        job_geo_id: LinkedIn geo ID if from job search

    Returns:
        company_id if successful, None otherwise
    """
    try:
        prisma = await get_prisma()
        result = await queries.insert_company(
            prisma,
            name=name,
            linkedin_username=linkedin_username,
            source=source,
            job_geo_id=job_geo_id,
        )

        if result:
            company_id = result.get("companyId")
            logger.info(f"Saved company: {name} (ID: {company_id})")
            return company_id
        return None

    except PrismaError as e:
        logger.error(f"Database error saving company {name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error saving company {name}: {e}")
        raise QueryError(f"Unexpected error saving company {name}: {e}") from e


async def save_companies_from_jobs(
    company_names: list[str],
    geo_id: str | None = None,
) -> list[int]:
    """
    Save multiple companies from job search results.

    Args:
        company_names: List of company names
        geo_id: LinkedIn geo ID the jobs were searched in

    Returns:
        List of company_ids that were saved
    """
    company_ids = []
    for name in company_names:
        company_id = await save_company(
            name=name,
            source="job_search",
            job_geo_id=geo_id,
        )
        if company_id:
            company_ids.append(company_id)
    return company_ids


async def get_companies_with_outreach_status(
    source: str | None = None,
) -> list[dict]:
    """
    Get all companies with their outreach status.

    Args:
        source: Optional filter by source (e.g., 'job_search')

    Returns:
        List of company dicts with outreach status
    """
    try:
        prisma = await get_prisma()
        results = await queries.get_companies_with_outreach_status(
            prisma, source=source
        )
        return results or []

    except PrismaError as e:
        logger.error(f"Database error getting companies: {e}")
        return []


async def update_company_outreach(
    company_id: int,
    status: str = "pending",
    employees_contacted: int = 0,
    notes: str | None = None,
) -> bool:
    """
    Update or create outreach status for a company.

    Args:
        company_id: Company ID
        status: Outreach status ('pending', 'in_progress', 'completed', 'skipped')
        employees_contacted: Number of employees contacted
        notes: Optional notes

    Returns:
        True if successful
    """
    try:
        prisma = await get_prisma()
        result = await queries.upsert_company_outreach(
            prisma,
            company_id=company_id,
            status=status,
            employees_contacted=employees_contacted,
            notes=notes,
        )
        return result is not None

    except PrismaError as e:
        logger.error(f"Database error updating outreach for company {company_id}: {e}")
        return False


async def increment_company_employees_contacted(company_id: int) -> int | None:
    """
    Increment the employees_contacted count for a company.

    Args:
        company_id: Company ID

    Returns:
        New count if successful, None otherwise
    """
    try:
        prisma = await get_prisma()
        result = await queries.increment_employees_contacted(
            prisma, company_id=company_id
        )
        if result:
            return result.get("employeesContacted")
        return None

    except PrismaError as e:
        logger.error(f"Database error incrementing employees for company {company_id}: {e}")
        return None
