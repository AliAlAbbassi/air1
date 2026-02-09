"""SEC EDGAR API client using edgartools library.

edgartools is synchronous, so all calls are wrapped with asyncio.to_thread()
to integrate with the async codebase. The library handles rate limiting,
caching, and retries internally.
"""

import asyncio
import math
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from loguru import logger

from air1.services.ingest.exceptions import FormDParsingError, SECAPIError
from air1.services.ingest.models import (
    SecCompanyData,
    SecCompanyProfile,
    SecFilingData,
    SecFormDData,
    SecOfficerData,
)


class SECClient:
    """Async wrapper around the edgartools library."""

    def __init__(self, identity: str):
        from edgar import set_identity

        set_identity(identity)
        logger.info(f"SEC EDGAR client initialized with identity: {identity}")

    async def fetch_company_tickers(self) -> list[SecCompanyData]:
        """Download the full list of ~10K public companies."""
        from edgar import get_company_tickers

        logger.info("Fetching company tickers from SEC EDGAR...")
        df = await asyncio.to_thread(get_company_tickers)

        def _clean(val):
            """Convert pandas NaN/None to None."""
            if val is None:
                return None
            if isinstance(val, float) and math.isnan(val):
                return None
            return str(val)

        companies = []
        for row in df.itertuples():
            companies.append(
                SecCompanyData(
                    cik=str(row.cik),
                    name=row.company,
                    ticker=_clean(row.ticker) if hasattr(row, "ticker") else None,
                    exchange=_clean(row.exchange) if hasattr(row, "exchange") else None,
                )
            )
        logger.info(f"Fetched {len(companies)} company tickers")
        return companies

    async def fetch_company_profile(self, cik: str) -> SecCompanyProfile:
        """Fetch enriched company profile from SEC submissions endpoint."""
        from edgar import Company

        try:
            company = await asyncio.to_thread(Company, cik)
            data = company.data
            addr = data.business_address

            return SecCompanyProfile(
                cik=cik,
                name=data.name or "",
                sic=str(data.sic) if data.sic else None,
                sic_description=data.sic_description if hasattr(data, "sic_description") else None,
                state_of_incorp=data.state_of_incorporation if hasattr(data, "state_of_incorporation") else None,
                fiscal_year_end=data.fiscal_year_end if hasattr(data, "fiscal_year_end") else None,
                street=addr.street1 if addr and hasattr(addr, "street1") else None,
                city=addr.city if addr and hasattr(addr, "city") else None,
                state_or_country=addr.state_or_country if addr and hasattr(addr, "state_or_country") else None,
                zip_code=addr.zipcode if addr and hasattr(addr, "zipcode") else None,
                phone=data.phone if hasattr(data, "phone") else None,
                website=data.website if hasattr(data, "website") else None,
            )
        except Exception as e:
            raise SECAPIError(f"Failed to fetch profile for CIK={cik}: {e}") from e

    async def fetch_form_d_filings(
        self, date_start: str, date_end: str
    ) -> list[SecFilingData]:
        """Fetch Form D filing index for a date range.

        Args:
            date_start: Start date in YYYY-MM-DD format.
            date_end: End date in YYYY-MM-DD format.
        """
        from edgar import get_filings

        try:
            logger.info(f"Fetching Form D filings from {date_start} to {date_end}...")
            filings = await asyncio.to_thread(
                get_filings, form="D", filing_date=f"{date_start}:{date_end}"
            )
            if filings is None or len(filings) == 0:
                logger.info("No Form D filings found for date range")
                return []

            df = filings.to_pandas()
            results = []
            for row in df.itertuples():
                results.append(
                    SecFilingData(
                        accession_number=row.accession_number,
                        cik=str(row.cik),
                        form_type=row.form,
                        filing_date=row.filing_date if isinstance(row.filing_date, date) else date.fromisoformat(str(row.filing_date)),
                        company_name=row.company if hasattr(row, "company") else None,
                    )
                )
            logger.info(f"Fetched {len(results)} Form D filings")
            return results
        except Exception as e:
            raise SECAPIError(f"Failed to fetch Form D filings: {e}") from e

    async def fetch_form_d_detail(
        self, accession_number: str
    ) -> SecFormDData:
        """Fetch and parse a single Form D filing's details."""
        from edgar import get_by_accession_number

        try:
            filing = await asyncio.to_thread(
                get_by_accession_number, accession_number
            )
            form_d = await asyncio.to_thread(filing.obj)

            return self._parse_form_d(form_d, accession_number, str(filing.cik), filing.filing_date)
        except FormDParsingError:
            raise
        except Exception as e:
            raise FormDParsingError(
                f"Failed to parse Form D {accession_number}: {e}"
            ) from e

    @staticmethod
    def _parse_form_d(form_d, accession_number: str, cik: str, filing_date) -> SecFormDData:
        """Extract structured data from an edgartools FormD object."""
        issuer = form_d.primary_issuer
        offering = form_d.offering_data

        # Parse offering amounts safely
        def _to_decimal(val) -> Optional[Decimal]:
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except (InvalidOperation, ValueError):
                return None

        # Extract offering sales amounts
        offering_amount = None
        amount_sold = None
        remaining = None
        if offering and hasattr(offering, "offering_sales_amounts"):
            osa = offering.offering_sales_amounts
            if osa:
                offering_amount = _to_decimal(getattr(osa, "total_offering_amount", None))
                amount_sold = _to_decimal(getattr(osa, "total_amount_sold", None))
                remaining = _to_decimal(getattr(osa, "total_remaining", None))

        # Parse date of first sale
        date_of_first_sale = None
        if offering and hasattr(offering, "date_of_first_sale"):
            raw_date = offering.date_of_first_sale
            if raw_date and raw_date != "Yet to occur":
                try:
                    date_of_first_sale = date.fromisoformat(str(raw_date))
                except (ValueError, TypeError):
                    pass

        # Parse officers
        officers = []
        for person in form_d.related_persons or []:
            addr = getattr(person, "address", None)
            officers.append(
                SecOfficerData(
                    first_name=getattr(person, "first_name", None),
                    last_name=getattr(person, "last_name", None),
                    title=None,  # edgartools Person doesn't expose title
                    street=addr.street1 if addr and hasattr(addr, "street1") else None,
                    city=addr.city if addr and hasattr(addr, "city") else None,
                    state=addr.state_or_country if addr and hasattr(addr, "state_or_country") else None,
                    zip_code=addr.zipcode if addr and hasattr(addr, "zipcode") else None,
                )
            )

        # Parse federal exemptions
        federal_exemptions = None
        if offering and hasattr(offering, "federal_exemptions"):
            exemptions = offering.federal_exemptions
            if exemptions:
                federal_exemptions = ",".join(str(e) for e in exemptions)

        # Parse industry group
        industry_group_type = None
        if offering and hasattr(offering, "industry_group"):
            ig = offering.industry_group
            if ig and hasattr(ig, "industry_group_type"):
                industry_group_type = str(ig.industry_group_type)

        filing_date_parsed = filing_date if isinstance(filing_date, date) else date.fromisoformat(str(filing_date))

        return SecFormDData(
            accession_number=accession_number,
            cik=cik,
            filing_date=filing_date_parsed,
            issuer_name=getattr(issuer, "entity_name", None) if issuer else None,
            issuer_street=issuer.primary_address.street1 if issuer and hasattr(issuer, "primary_address") and issuer.primary_address else None,
            issuer_city=issuer.primary_address.city if issuer and hasattr(issuer, "primary_address") and issuer.primary_address else None,
            issuer_state=getattr(issuer, "jurisdiction", None) if issuer else None,
            issuer_zip=issuer.primary_address.zipcode if issuer and hasattr(issuer, "primary_address") and issuer.primary_address else None,
            issuer_phone=getattr(issuer, "phone_number", None) if issuer else None,
            entity_type=getattr(issuer, "entity_type", None) if issuer else None,
            industry_group_type=industry_group_type,
            revenue_range=getattr(offering, "revenue_range", None) if offering else None,
            federal_exemptions=federal_exemptions,
            total_offering_amount=offering_amount,
            total_amount_sold=amount_sold,
            total_remaining=remaining,
            date_of_first_sale=date_of_first_sale,
            officers=officers,
        )
