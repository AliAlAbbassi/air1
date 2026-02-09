"""Repository functions for SEC ingest data persistence.

Error Handling Contract:
- PrismaError: return failure indicator (False, None, empty list), log at ERROR
- Unexpected errors: raise domain exceptions (CompanyInsertionError, etc.)
"""

from loguru import logger
from prisma.errors import PrismaError

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import ingest_queries as queries
from air1.services.ingest.exceptions import (
    CompanyInsertionError,
    FilingInsertionError,
    QueryError,
)
from air1.services.ingest.models import (
    SecCompanyData,
    SecCompanyProfile,
    SecFilingData,
    SecFormDData,
)


async def upsert_company(company: SecCompanyData) -> tuple[bool, int | None]:
    """Insert or update a SEC company. Returns (success, sec_company_id)."""
    try:
        prisma = await get_prisma()
        result = await queries.upsert_sec_company(
            prisma,
            cik=company.cik,
            name=company.name,
            ticker=company.ticker,
            exchange=company.exchange,
        )
        if result:
            return True, result["secCompanyId"]
        return False, None
    except PrismaError as e:
        logger.error(f"Database error upserting SEC company CIK={company.cik}: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error upserting SEC company CIK={company.cik}: {e}")
        raise CompanyInsertionError(
            f"Failed to upsert company CIK={company.cik}: {e}"
        ) from e


async def upsert_companies_batch(companies: list[SecCompanyData]) -> int:
    """Batch upsert companies. Returns count of successful inserts."""
    success_count = 0
    for company in companies:
        ok, _ = await upsert_company(company)
        if ok:
            success_count += 1
    return success_count


async def enrich_company(profile: SecCompanyProfile) -> bool:
    """Update a company with enriched data from submissions endpoint."""
    try:
        prisma = await get_prisma()
        await queries.enrich_sec_company(
            prisma,
            cik=profile.cik,
            sic=profile.sic,
            sic_description=profile.sic_description,
            state_of_incorp=profile.state_of_incorp,
            fiscal_year_end=profile.fiscal_year_end,
            street=profile.street,
            city=profile.city,
            state_or_country=profile.state_or_country,
            zip_code=profile.zip_code,
            phone=profile.phone,
            website=profile.website,
        )
        return True
    except PrismaError as e:
        logger.error(f"Database error enriching company CIK={profile.cik}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error enriching company CIK={profile.cik}: {e}")
        raise CompanyInsertionError(
            f"Failed to enrich company CIK={profile.cik}: {e}"
        ) from e


async def get_companies_not_enriched(limit: int = 500) -> list[dict]:
    """Get companies that haven't been enriched yet."""
    try:
        prisma = await get_prisma()
        return await queries.get_sec_companies_not_enriched(prisma, limit=limit) or []
    except PrismaError as e:
        logger.error(f"Database error getting unenriched companies: {e}")
        return []
    except Exception as e:
        raise QueryError(f"Failed to get unenriched companies: {e}") from e


async def count_companies() -> int:
    """Count total SEC companies."""
    try:
        prisma = await get_prisma()
        result = await queries.count_sec_companies(prisma)
        return result or 0
    except PrismaError as e:
        logger.error(f"Database error counting companies: {e}")
        return 0


async def count_companies_not_enriched() -> int:
    """Count unenriched SEC companies."""
    try:
        prisma = await get_prisma()
        result = await queries.count_sec_companies_not_enriched(prisma)
        return result or 0
    except PrismaError as e:
        logger.error(f"Database error counting unenriched companies: {e}")
        return 0


async def upsert_filing(filing: SecFilingData) -> tuple[bool, int | None]:
    """Insert or update a SEC filing. Returns (success, sec_filing_id)."""
    try:
        prisma = await get_prisma()
        result = await queries.upsert_sec_filing(
            prisma,
            accession_number=filing.accession_number,
            cik=filing.cik,
            form_type=filing.form_type,
            filing_date=filing.filing_date.isoformat(),
            company_name=filing.company_name,
        )
        if result:
            return True, result["secFilingId"]
        return False, None
    except PrismaError as e:
        logger.error(
            f"Database error upserting filing {filing.accession_number}: {e}"
        )
        return False, None
    except Exception as e:
        logger.error(
            f"Unexpected error upserting filing {filing.accession_number}: {e}"
        )
        raise FilingInsertionError(
            f"Failed to upsert filing {filing.accession_number}: {e}"
        ) from e


async def get_form_d_filings_not_parsed(limit: int = 100) -> list[dict]:
    """Get Form D filings that haven't been parsed yet."""
    try:
        prisma = await get_prisma()
        return (
            await queries.get_form_d_filings_not_parsed(prisma, limit=limit) or []
        )
    except PrismaError as e:
        logger.error(f"Database error getting unparsed Form D filings: {e}")
        return []
    except Exception as e:
        raise QueryError(f"Failed to get unparsed Form D filings: {e}") from e


async def save_form_d_complete(
    form_d: SecFormDData, sec_filing_id: int
) -> tuple[bool, int | None]:
    """Save Form D data with officers. Returns (success, sec_form_d_id)."""
    try:
        prisma = await get_prisma()

        form_d_result = await queries.upsert_sec_form_d(
            prisma,
            sec_filing_id=sec_filing_id,
            issuer_name=form_d.issuer_name,
            issuer_street=form_d.issuer_street,
            issuer_city=form_d.issuer_city,
            issuer_state=form_d.issuer_state,
            issuer_zip=form_d.issuer_zip,
            issuer_phone=form_d.issuer_phone,
            entity_type=form_d.entity_type,
            industry_group_type=form_d.industry_group_type,
            revenue_range=form_d.revenue_range,
            federal_exemptions=form_d.federal_exemptions,
            total_offering_amount=str(form_d.total_offering_amount) if form_d.total_offering_amount is not None else None,
            total_amount_sold=str(form_d.total_amount_sold) if form_d.total_amount_sold is not None else None,
            total_remaining=str(form_d.total_remaining) if form_d.total_remaining is not None else None,
            date_of_first_sale=form_d.date_of_first_sale.isoformat() if form_d.date_of_first_sale else None,
        )
        if not form_d_result:
            return False, None

        form_d_id = form_d_result["secFormDId"]

        for officer in form_d.officers:
            await queries.insert_sec_officer(
                prisma,
                sec_form_d_id=form_d_id,
                first_name=officer.first_name,
                last_name=officer.last_name,
                title=officer.title,
                street=officer.street,
                city=officer.city,
                state=officer.state,
                zip_code=officer.zip_code,
            )

        return True, form_d_id
    except PrismaError as e:
        logger.error(f"Database error saving Form D {form_d.accession_number}: {e}")
        return False, None
    except Exception as e:
        logger.error(
            f"Unexpected error saving Form D {form_d.accession_number}: {e}"
        )
        raise FilingInsertionError(
            f"Failed to save Form D {form_d.accession_number}: {e}"
        ) from e
