"""SEC EDGAR API client using edgartools library.

edgartools is synchronous, so all calls are wrapped with asyncio.to_thread()
to integrate with the async codebase. The library handles rate limiting,
caching, and retries internally.
"""

import asyncio
import math
from datetime import date, timedelta
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
        """Fetch Form D filing index for a date range (downloads full quarterly index).

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
            return self._filings_to_list(filings)
        except Exception as e:
            raise SECAPIError(f"Failed to fetch Form D filings: {e}") from e

    async def fetch_daily_form_d_filings(self, date_str: Optional[str] = None) -> list[SecFilingData]:
        """Fetch Form D filings for a single day using the daily index (efficient).

        Args:
            date_str: Date in YYYY-MM-DD format. Defaults to yesterday.
        """
        from edgar._filings import Filings, fetch_daily_filing_index

        if date_str is None:
            date_str = (date.today() - timedelta(days=1)).isoformat()

        try:
            logger.info(f"Fetching daily Form D index for {date_str}...")
            table = await asyncio.to_thread(fetch_daily_filing_index, date_str)
            filings = Filings(table)
            form_d = filings.filter(form="D")
            return self._filings_to_list(form_d)
        except Exception as e:
            raise SECAPIError(f"Failed to fetch daily Form D filings for {date_str}: {e}") from e

    async def fetch_current_form_d_filings(self) -> list[SecFilingData]:
        """Fetch real-time Form D filings from SEC current feed (~24 hours)."""
        from edgar import get_current_filings

        try:
            logger.info("Fetching current Form D filings from SEC feed...")
            filings = await asyncio.to_thread(
                get_current_filings, form="D", page_size=None
            )
            return self._filings_to_list(filings)
        except Exception as e:
            raise SECAPIError(f"Failed to fetch current Form D filings: {e}") from e

    def _filings_to_list(self, filings) -> list[SecFilingData]:
        """Convert an edgartools Filings object to a list of SecFilingData."""
        if filings is None or len(filings) == 0:
            logger.info("No Form D filings found")
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

        def _to_decimal(val) -> Optional[Decimal]:
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except (InvalidOperation, ValueError):
                return None

        def _to_int(val) -> Optional[int]:
            if val is None:
                return None
            try:
                return int(str(val))
            except (ValueError, TypeError):
                return None

        def _to_bool(val) -> Optional[bool]:
            if val is None:
                return None
            if isinstance(val, bool):
                return val
            s = str(val).lower()
            if s in ("true", "yes", "y", "1"):
                return True
            if s in ("false", "no", "n", "0"):
                return False
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

        # Extract additional offering fields
        minimum_investment = None
        total_investors = None
        has_non_accredited_investors = None
        is_equity = None
        is_pooled_investment = None
        is_new_offering = None
        more_than_one_year = None
        is_business_combination = None
        sales_commission = None
        finders_fees = None
        gross_proceeds_used = None

        if offering:
            minimum_investment = _to_decimal(getattr(offering, "minimum_investment", None))
            is_equity = _to_bool(getattr(offering, "is_equity", None))
            is_pooled_investment = _to_bool(getattr(offering, "is_pooled_investment", None))
            # edgartools `is_new` is actually `isAmendment` (True = amendment, not new)
            _is_amendment = _to_bool(getattr(offering, "is_new", None))
            is_new_offering = not _is_amendment if _is_amendment is not None else None
            more_than_one_year = _to_bool(getattr(offering, "more_than_one_year", None))

            # Investors
            investors = getattr(offering, "investors", None)
            if investors:
                total_investors = _to_int(getattr(investors, "total_already_invested", None))
                has_non_accredited_investors = _to_bool(
                    getattr(investors, "has_non_accredited_investors", None)
                )

            # Business combination
            bct = getattr(offering, "business_combination_transaction", None)
            if bct:
                is_business_combination = _to_bool(
                    getattr(bct, "is_business_combination", None)
                )

            # Sales commission and finder's fees
            scff = getattr(offering, "sales_commission_finders_fees", None)
            if scff:
                sales_commission = _to_decimal(getattr(scff, "sales_commission", None))
                finders_fees = _to_decimal(getattr(scff, "finders_fees", None))

            # Use of proceeds
            uop = getattr(offering, "use_of_proceeds", None)
            if uop:
                gross_proceeds_used = _to_decimal(getattr(uop, "gross_proceeds_used", None))

        # Build title lookup from signature block
        title_map: dict[str, str] = {}
        sig_block = getattr(form_d, "signature_block", None)
        if sig_block:
            for sig in getattr(sig_block, "signatures", None) or []:
                title = getattr(sig, "title", None)
                if not title:
                    continue
                signer_name = getattr(sig, "name_of_signer", None) or ""
                sig_name = getattr(sig, "signature_name", None) or ""
                for name in (signer_name, sig_name):
                    name_key = name.strip().lower()
                    if name_key:
                        title_map[name_key] = str(title)

        # Parse officers with title cross-reference
        officers = []
        for person in form_d.related_persons or []:
            addr = getattr(person, "address", None)
            first = getattr(person, "first_name", None)
            last = getattr(person, "last_name", None)

            # Try to find title from signature block (full name only to avoid mismatches)
            person_title = None
            if first and last:
                full_name = f"{first} {last}".strip().lower()
                person_title = title_map.get(full_name)

            officers.append(
                SecOfficerData(
                    first_name=first,
                    last_name=last,
                    title=person_title,
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
            issuer_street=getattr(issuer.primary_address, "street1", None) if issuer and getattr(issuer, "primary_address", None) else None,
            issuer_city=getattr(issuer.primary_address, "city", None) if issuer and getattr(issuer, "primary_address", None) else None,
            issuer_state=getattr(issuer, "jurisdiction", None) if issuer else None,
            issuer_zip=getattr(issuer.primary_address, "zipcode", None) if issuer and getattr(issuer, "primary_address", None) else None,
            issuer_phone=getattr(issuer, "phone_number", None) if issuer else None,
            entity_type=getattr(issuer, "entity_type", None) if issuer else None,
            industry_group_type=industry_group_type,
            revenue_range=getattr(offering, "revenue_range", None) if offering else None,
            federal_exemptions=federal_exemptions,
            total_offering_amount=offering_amount,
            total_amount_sold=amount_sold,
            total_remaining=remaining,
            date_of_first_sale=date_of_first_sale,
            minimum_investment=minimum_investment,
            total_investors=total_investors,
            has_non_accredited_investors=has_non_accredited_investors,
            is_equity=is_equity,
            is_pooled_investment=is_pooled_investment,
            is_new_offering=is_new_offering,
            more_than_one_year=more_than_one_year,
            is_business_combination=is_business_combination,
            sales_commission=sales_commission,
            finders_fees=finders_fees,
            gross_proceeds_used=gross_proceeds_used,
            officers=officers,
        )
