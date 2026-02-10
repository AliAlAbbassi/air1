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
    """Batch upsert companies via multi-row INSERT. Returns count stored."""
    if not companies:
        return 0
    try:
        prisma = await get_prisma()
        # Dedupe by CIK (last wins) — Postgres ON CONFLICT can't handle dupes in same INSERT
        seen: dict[str, SecCompanyData] = {}
        for c in companies:
            seen[c.cik] = c
        deduped = list(seen.values())
        chunk_size = 1000
        total = 0
        for i in range(0, len(deduped), chunk_size):
            chunk = deduped[i : i + chunk_size]
            placeholders = []
            params: list = []
            for j, c in enumerate(chunk):
                off = j * 4
                placeholders.append(f"(${off+1}, ${off+2}, ${off+3}, ${off+4})")
                params.extend([c.cik, c.name, c.ticker, c.exchange])
            values_sql = ", ".join(placeholders)
            sql = f"""
                INSERT INTO sec_company (cik, name, ticker, exchange)
                VALUES {values_sql}
                ON CONFLICT (cik) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, sec_company.name),
                    ticker = COALESCE(EXCLUDED.ticker, sec_company.ticker),
                    exchange = COALESCE(EXCLUDED.exchange, sec_company.exchange),
                    updated_on = NOW()
            """
            total += await prisma.execute_raw(sql, *params)
        return total
    except PrismaError as e:
        logger.error(f"Database error batch upserting {len(companies)} companies: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error batch upserting companies: {e}")
        raise CompanyInsertionError(
            f"Failed to batch upsert {len(companies)} companies: {e}"
        ) from e


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


async def enrich_companies_batch(profiles: list[SecCompanyProfile]) -> int:
    """Batch update companies with enriched data. Returns count updated."""
    if not profiles:
        return 0
    try:
        prisma = await get_prisma()
        chunk_size = 1000
        total = 0
        for i in range(0, len(profiles), chunk_size):
            chunk = profiles[i : i + chunk_size]
            placeholders = []
            params: list = []
            for j, p in enumerate(chunk):
                off = j * 11
                placeholders.append(
                    f"(${off+1}, ${off+2}, ${off+3}, ${off+4}, ${off+5}, "
                    f"${off+6}, ${off+7}, ${off+8}, ${off+9}, ${off+10}, ${off+11})"
                )
                params.extend([
                    p.cik,
                    p.sic,
                    p.sic_description,
                    p.state_of_incorp,
                    p.fiscal_year_end,
                    p.street,
                    p.city,
                    p.state_or_country,
                    p.zip_code,
                    p.phone,
                    p.website,
                ])
            values_sql = ", ".join(placeholders)
            sql = f"""
                UPDATE sec_company SET
                    sic = COALESCE(v.sic, sec_company.sic),
                    sic_description = COALESCE(v.sic_desc, sec_company.sic_description),
                    state_of_incorp = COALESCE(v.state_of_incorp, sec_company.state_of_incorp),
                    fiscal_year_end = COALESCE(v.fiscal_year_end, sec_company.fiscal_year_end),
                    street = COALESCE(v.street, sec_company.street),
                    city = COALESCE(v.city, sec_company.city),
                    state_or_country = COALESCE(v.state_or_country, sec_company.state_or_country),
                    zip_code = COALESCE(v.zip_code, sec_company.zip_code),
                    phone = COALESCE(v.phone, sec_company.phone),
                    website = COALESCE(v.website, sec_company.website),
                    enriched_at = NOW(),
                    updated_on = NOW()
                FROM (VALUES {values_sql}) AS v(cik, sic, sic_desc, state_of_incorp, fiscal_year_end, street, city, state_or_country, zip_code, phone, website)
                WHERE sec_company.cik = v.cik
            """
            total += await prisma.execute_raw(sql, *params)
        return total
    except PrismaError as e:
        logger.error(f"Database error batch enriching {len(profiles)} companies: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error batch enriching companies: {e}")
        raise CompanyInsertionError(
            f"Failed to batch enrich {len(profiles)} companies: {e}"
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


async def upsert_company_from_issuer(
    cik: str,
    name: str,
    street: str | None = None,
    city: str | None = None,
    state_or_country: str | None = None,
    zip_code: str | None = None,
    phone: str | None = None,
) -> tuple[bool, int | None]:
    """Create or update a company from Form D issuer data. Returns (success, sec_company_id)."""
    try:
        prisma = await get_prisma()
        result = await queries.upsert_sec_company_from_issuer(
            prisma,
            cik=cik,
            name=name,
            street=street,
            city=city,
            state_or_country=state_or_country,
            zip_code=zip_code,
            phone=phone,
        )
        if result:
            return True, result["secCompanyId"]
        return False, None
    except PrismaError as e:
        logger.error(f"Database error upserting company from issuer CIK={cik}: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error upserting company from issuer CIK={cik}: {e}")
        raise CompanyInsertionError(
            f"Failed to upsert company from issuer CIK={cik}: {e}"
        ) from e


async def upsert_companies_from_issuers_batch(
    issuers: list[tuple[str, str, str | None, str | None, str | None, str | None, str | None]],
) -> int:
    """Batch upsert companies from Form D issuer data. Returns count stored.

    Each tuple: (cik, name, street, city, state_or_country, zip_code, phone).
    """
    if not issuers:
        return 0
    try:
        prisma = await get_prisma()
        chunk_size = 1000
        total = 0
        for i in range(0, len(issuers), chunk_size):
            chunk = issuers[i : i + chunk_size]
            placeholders = []
            params: list = []
            for j, row in enumerate(chunk):
                off = j * 7
                placeholders.append(
                    f"(${off+1}, ${off+2}, ${off+3}, ${off+4}, ${off+5}, ${off+6}, ${off+7})"
                )
                params.extend(row)
            values_sql = ", ".join(placeholders)
            sql = f"""
                INSERT INTO sec_company (cik, name, street, city, state_or_country, zip_code, phone)
                VALUES {values_sql}
                ON CONFLICT (cik) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, sec_company.name),
                    street = COALESCE(EXCLUDED.street, sec_company.street),
                    city = COALESCE(EXCLUDED.city, sec_company.city),
                    state_or_country = COALESCE(EXCLUDED.state_or_country, sec_company.state_or_country),
                    zip_code = COALESCE(EXCLUDED.zip_code, sec_company.zip_code),
                    phone = COALESCE(EXCLUDED.phone, sec_company.phone),
                    updated_on = NOW()
            """
            total += await prisma.execute_raw(sql, *params)
        return total
    except PrismaError as e:
        logger.error(f"Database error batch upserting {len(issuers)} issuer companies: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error batch upserting issuer companies: {e}")
        raise CompanyInsertionError(
            f"Failed to batch upsert {len(issuers)} issuer companies: {e}"
        ) from e


async def link_orphaned_filings() -> None:
    """Link filings with sec_company_id=NULL to their companies by CIK."""
    try:
        prisma = await get_prisma()
        await queries.link_orphaned_filings(prisma)
        logger.info("Linked orphaned filings to companies")
    except PrismaError as e:
        logger.error(f"Database error linking orphaned filings: {e}")
    except Exception as e:
        raise QueryError(f"Failed to link orphaned filings: {e}") from e


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


async def upsert_filings_batch(filings: list[SecFilingData]) -> int:
    """Batch upsert filings in a single SQL query. Returns count stored."""
    if not filings:
        return 0
    try:
        prisma = await get_prisma()
        # Dedupe by accession_number (last wins) — ON CONFLICT can't handle dupes in same INSERT
        seen: dict[str, SecFilingData] = {}
        for f in filings:
            seen[f.accession_number] = f
        filings = list(seen.values())
        # Build multi-row VALUES for a single INSERT
        placeholders = []
        params: list = []
        for i, f in enumerate(filings):
            off = i * 5
            placeholders.append(
                f"(${off+1}, ${off+2}, ${off+3}, ${off+4}::DATE, ${off+5})"
            )
            params.extend([
                f.accession_number,
                f.cik,
                f.form_type,
                f.filing_date.isoformat(),
                f.company_name,
            ])
        values_sql = ", ".join(placeholders)
        sql = f"""
            INSERT INTO sec_filing (accession_number, cik, form_type, filing_date, company_name)
            VALUES {values_sql}
            ON CONFLICT (accession_number) DO UPDATE SET
                form_type = EXCLUDED.form_type,
                company_name = COALESCE(EXCLUDED.company_name, sec_filing.company_name),
                updated_on = NOW()
        """
        await prisma.execute_raw(sql, *params)
        return len(filings)
    except PrismaError as e:
        logger.error(f"Database error batch upserting {len(filings)} filings: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error batch upserting filings: {e}")
        raise FilingInsertionError(
            f"Failed to batch upsert {len(filings)} filings: {e}"
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
    """Save Form D data with officers atomically. Returns (success, sec_form_d_id).

    Uses a database transaction so that if any officer insert fails,
    the entire operation is rolled back (no partial state).
    """
    try:
        prisma = await get_prisma()

        def _dec(val):
            return str(val) if val is not None else None

        def _bool(val):
            return str(val).lower() if val is not None else None

        # Begin transaction
        await prisma.query_raw("BEGIN")
        try:
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
                total_offering_amount=_dec(form_d.total_offering_amount),
                total_amount_sold=_dec(form_d.total_amount_sold),
                total_remaining=_dec(form_d.total_remaining),
                date_of_first_sale=form_d.date_of_first_sale.isoformat() if form_d.date_of_first_sale else None,
                minimum_investment=_dec(form_d.minimum_investment),
                total_investors=str(form_d.total_investors) if form_d.total_investors is not None else None,
                has_non_accredited_investors=_bool(form_d.has_non_accredited_investors),
                is_equity=_bool(form_d.is_equity),
                is_pooled_investment=_bool(form_d.is_pooled_investment),
                is_new_offering=_bool(form_d.is_new_offering),
                more_than_one_year=_bool(form_d.more_than_one_year),
                is_business_combination=_bool(form_d.is_business_combination),
                sales_commission=_dec(form_d.sales_commission),
                finders_fees=_dec(form_d.finders_fees),
                gross_proceeds_used=_dec(form_d.gross_proceeds_used),
            )
            if not form_d_result:
                await prisma.query_raw("ROLLBACK")
                return False, None

            form_d_id = form_d_result["secFormDId"]

            # Delete existing officers before re-inserting (prevents duplicates on re-parse)
            await queries.delete_officers_by_form_d(prisma, sec_form_d_id=form_d_id)

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

            await prisma.query_raw("COMMIT")
            return True, form_d_id
        except Exception:
            await prisma.query_raw("ROLLBACK")
            raise
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


async def save_form_d_batch(
    items: list[tuple[SecFormDData, int]],
) -> int:
    """Batch save Form D records with officers in 3 queries + transaction.

    Each item is (SecFormDData, sec_filing_id). Returns count saved.
    """
    if not items:
        return 0

    def _dec(val):
        return str(val) if val is not None else None

    def _bool(val):
        return str(val).lower() if val is not None else None

    try:
        prisma = await get_prisma()
        # Dedupe by sec_filing_id (last wins)
        seen: dict[int, tuple[SecFormDData, int]] = {}
        for fd, fid in items:
            seen[fid] = (fd, fid)
        items = list(seen.values())
        await prisma.query_raw("BEGIN")
        try:
            # Step 1: Multi-row INSERT for form_d records with RETURNING
            chunk_size = 1000
            form_d_ids: list[int] = []  # parallel to items

            for i in range(0, len(items), chunk_size):
                chunk = items[i : i + chunk_size]
                placeholders = []
                params: list = []
                for j, (fd, filing_id) in enumerate(chunk):
                    off = j * 26
                    placeholders.append(
                        f"(${off+1}::INT, ${off+2}, ${off+3}, ${off+4}, "
                        f"${off+5}, ${off+6}, ${off+7}, ${off+8}, "
                        f"${off+9}, ${off+10}, ${off+11}, "
                        f"CAST(${off+12} AS DECIMAL(20,2)), CAST(${off+13} AS DECIMAL(20,2)), CAST(${off+14} AS DECIMAL(20,2)), "
                        f"CAST(${off+15} AS DATE), CAST(${off+16} AS DECIMAL(20,2)), CAST(${off+17} AS INTEGER), "
                        f"CAST(${off+18} AS BOOLEAN), CAST(${off+19} AS BOOLEAN), CAST(${off+20} AS BOOLEAN), "
                        f"CAST(${off+21} AS BOOLEAN), CAST(${off+22} AS BOOLEAN), CAST(${off+23} AS BOOLEAN), "
                        f"CAST(${off+24} AS DECIMAL(20,2)), CAST(${off+25} AS DECIMAL(20,2)), CAST(${off+26} AS DECIMAL(20,2)))"
                    )
                    params.extend([
                        filing_id,
                        fd.issuer_name,
                        fd.issuer_street,
                        fd.issuer_city,
                        fd.issuer_state,
                        fd.issuer_zip,
                        fd.issuer_phone,
                        fd.entity_type,
                        fd.industry_group_type,
                        fd.revenue_range,
                        fd.federal_exemptions,
                        _dec(fd.total_offering_amount),
                        _dec(fd.total_amount_sold),
                        _dec(fd.total_remaining),
                        fd.date_of_first_sale.isoformat() if fd.date_of_first_sale else None,
                        _dec(fd.minimum_investment),
                        str(fd.total_investors) if fd.total_investors is not None else None,
                        _bool(fd.has_non_accredited_investors),
                        _bool(fd.is_equity),
                        _bool(fd.is_pooled_investment),
                        _bool(fd.is_new_offering),
                        _bool(fd.more_than_one_year),
                        _bool(fd.is_business_combination),
                        _dec(fd.sales_commission),
                        _dec(fd.finders_fees),
                        _dec(fd.gross_proceeds_used),
                    ])
                values_sql = ", ".join(placeholders)
                sql = f"""
                    INSERT INTO sec_form_d (
                        sec_filing_id, issuer_name, issuer_street, issuer_city,
                        issuer_state, issuer_zip, issuer_phone, entity_type,
                        industry_group_type, revenue_range, federal_exemptions,
                        total_offering_amount, total_amount_sold, total_remaining,
                        date_of_first_sale, minimum_investment, total_investors,
                        has_non_accredited_investors, is_equity, is_pooled_investment,
                        is_new_offering, more_than_one_year, is_business_combination,
                        sales_commission, finders_fees, gross_proceeds_used
                    )
                    VALUES {values_sql}
                    ON CONFLICT (sec_filing_id) DO UPDATE SET
                        issuer_name = COALESCE(EXCLUDED.issuer_name, sec_form_d.issuer_name),
                        issuer_street = COALESCE(EXCLUDED.issuer_street, sec_form_d.issuer_street),
                        issuer_city = COALESCE(EXCLUDED.issuer_city, sec_form_d.issuer_city),
                        issuer_state = COALESCE(EXCLUDED.issuer_state, sec_form_d.issuer_state),
                        issuer_zip = COALESCE(EXCLUDED.issuer_zip, sec_form_d.issuer_zip),
                        issuer_phone = COALESCE(EXCLUDED.issuer_phone, sec_form_d.issuer_phone),
                        entity_type = COALESCE(EXCLUDED.entity_type, sec_form_d.entity_type),
                        industry_group_type = COALESCE(EXCLUDED.industry_group_type, sec_form_d.industry_group_type),
                        revenue_range = COALESCE(EXCLUDED.revenue_range, sec_form_d.revenue_range),
                        federal_exemptions = COALESCE(EXCLUDED.federal_exemptions, sec_form_d.federal_exemptions),
                        total_offering_amount = COALESCE(EXCLUDED.total_offering_amount, sec_form_d.total_offering_amount),
                        total_amount_sold = COALESCE(EXCLUDED.total_amount_sold, sec_form_d.total_amount_sold),
                        total_remaining = COALESCE(EXCLUDED.total_remaining, sec_form_d.total_remaining),
                        date_of_first_sale = COALESCE(EXCLUDED.date_of_first_sale, sec_form_d.date_of_first_sale),
                        minimum_investment = COALESCE(EXCLUDED.minimum_investment, sec_form_d.minimum_investment),
                        total_investors = COALESCE(EXCLUDED.total_investors, sec_form_d.total_investors),
                        has_non_accredited_investors = COALESCE(EXCLUDED.has_non_accredited_investors, sec_form_d.has_non_accredited_investors),
                        is_equity = COALESCE(EXCLUDED.is_equity, sec_form_d.is_equity),
                        is_pooled_investment = COALESCE(EXCLUDED.is_pooled_investment, sec_form_d.is_pooled_investment),
                        is_new_offering = COALESCE(EXCLUDED.is_new_offering, sec_form_d.is_new_offering),
                        more_than_one_year = COALESCE(EXCLUDED.more_than_one_year, sec_form_d.more_than_one_year),
                        is_business_combination = COALESCE(EXCLUDED.is_business_combination, sec_form_d.is_business_combination),
                        sales_commission = COALESCE(EXCLUDED.sales_commission, sec_form_d.sales_commission),
                        finders_fees = COALESCE(EXCLUDED.finders_fees, sec_form_d.finders_fees),
                        gross_proceeds_used = COALESCE(EXCLUDED.gross_proceeds_used, sec_form_d.gross_proceeds_used),
                        updated_on = NOW()
                    RETURNING sec_form_d_id AS "secFormDId"
                """
                rows = await prisma.query_raw(sql, *params)
                form_d_ids.extend(r["secFormDId"] for r in rows)

            # Step 2: Delete all existing officers for these form_d records
            if form_d_ids:
                await prisma.execute_raw(
                    "DELETE FROM sec_officer WHERE sec_form_d_id = ANY($1::int[])",
                    form_d_ids,
                )

            # Step 3: Multi-row INSERT for all officers
            all_officers: list[tuple] = []
            for (fd, _), fid in zip(items, form_d_ids):
                for off_data in fd.officers:
                    all_officers.append((
                        fid,
                        off_data.first_name,
                        off_data.last_name,
                        off_data.title,
                        off_data.street,
                        off_data.city,
                        off_data.state,
                        off_data.zip_code,
                    ))

            for i in range(0, len(all_officers), chunk_size):
                chunk = all_officers[i : i + chunk_size]
                placeholders = []
                params = []
                for j, row in enumerate(chunk):
                    off = j * 8
                    placeholders.append(
                        f"(${off+1}::INT, ${off+2}, ${off+3}, ${off+4}, ${off+5}, ${off+6}, ${off+7}, ${off+8})"
                    )
                    params.extend(row)
                values_sql = ", ".join(placeholders)
                sql = f"""
                    INSERT INTO sec_officer (sec_form_d_id, first_name, last_name, title, street, city, state, zip_code)
                    VALUES {values_sql}
                """
                await prisma.execute_raw(sql, *params)

            await prisma.query_raw("COMMIT")
            return len(form_d_ids)
        except Exception:
            await prisma.query_raw("ROLLBACK")
            raise
    except PrismaError as e:
        logger.error(f"Database error batch saving {len(items)} Form D records: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error batch saving Form D records: {e}")
        raise FilingInsertionError(
            f"Failed to batch save {len(items)} Form D records: {e}"
        ) from e
