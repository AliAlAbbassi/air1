"""SEC EDGAR ingestion service.

Orchestrates SEC EDGAR data fetching and database persistence.
Uses edgartools for API access and the repo layer for storage.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

from loguru import logger

from air1.services.ingest import repo
from air1.services.ingest.sec_client import SECClient


class IService(ABC):
    """Service interface for SEC EDGAR ingestion."""

    @abstractmethod
    async def bootstrap_companies(self) -> int:
        """Download all public company tickers and upsert into database."""
        ...

    @abstractmethod
    async def enrich_companies(self, batch_size: int = 500) -> int:
        """Fetch SEC profiles for unenriched companies in one batch."""
        ...

    @abstractmethod
    async def ingest_form_d_filings(
        self,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        days: int = 30,
    ) -> int:
        """Fetch Form D filing index for a date range and store."""
        ...

    @abstractmethod
    async def parse_form_d_details(self, batch_size: int = 100) -> int:
        """Parse unparsed Form D filings to extract issuer, offering, and officers."""
        ...


class Service(IService):
    """SEC EDGAR ingestion service.

    Usage:
        async with Service(identity="Company email@co.com") as svc:
            await svc.bootstrap_companies()
    """

    def __init__(self, identity: str):
        self._identity = identity
        self._client: Optional[SECClient] = None

    async def __aenter__(self):
        self._client = SECClient(identity=self._identity)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._client = None

    async def bootstrap_companies(self) -> int:
        """Download all ~10K public company tickers and upsert into database."""
        logger.info("Bootstrapping SEC companies...")
        companies = await self._client.fetch_company_tickers()
        logger.info(f"Fetched {len(companies)} companies from SEC EDGAR")
        count = await repo.upsert_companies_batch(companies)
        logger.info(f"Upserted {count}/{len(companies)} companies")
        return count

    async def enrich_companies(self, batch_size: int = 500) -> int:
        """Fetch SEC profiles for unenriched companies.

        Processes one batch. Call repeatedly to enrich all.
        Returns count of successfully enriched companies.
        """
        unenriched = await repo.get_companies_not_enriched(limit=batch_size)
        if not unenriched:
            logger.info("No unenriched companies remaining")
            return 0

        logger.info(f"Enriching {len(unenriched)} companies...")
        enriched = 0
        for row in unenriched:
            try:
                profile = await self._client.fetch_company_profile(row["cik"])
                ok = await repo.enrich_company(profile)
                if ok:
                    enriched += 1
            except Exception as e:
                logger.warning(f"Failed to enrich CIK={row['cik']}: {e}")
        logger.info(f"Enriched {enriched}/{len(unenriched)} companies")
        return enriched

    async def ingest_form_d_filings(
        self,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        days: int = 30,
    ) -> int:
        """Fetch Form D filing index for a date range and store.

        Args:
            date_start: Start date (YYYY-MM-DD). Defaults to `days` ago.
            date_end: End date (YYYY-MM-DD). Defaults to today.
            days: Number of days back if date_start not specified.

        Returns count of filings stored.
        """
        if date_end is None:
            date_end = date.today().isoformat()
        if date_start is None:
            date_start = (date.today() - timedelta(days=days)).isoformat()

        filings = await self._client.fetch_form_d_filings(date_start, date_end)
        if not filings:
            return 0

        stored = 0
        for filing in filings:
            ok, _ = await repo.upsert_filing(filing)
            if ok:
                stored += 1
        logger.info(f"Stored {stored}/{len(filings)} Form D filings")
        return stored

    async def parse_form_d_details(self, batch_size: int = 100) -> int:
        """Parse unparsed Form D filings to extract issuer, offering, and officers.

        Returns count of successfully parsed filings.
        """
        unparsed = await repo.get_form_d_filings_not_parsed(limit=batch_size)
        if not unparsed:
            logger.info("No unparsed Form D filings remaining")
            return 0

        logger.info(f"Parsing {len(unparsed)} Form D filings...")
        parsed = 0
        for row in unparsed:
            try:
                form_d = await self._client.fetch_form_d_detail(
                    row["accessionNumber"]
                )
                ok, _ = await repo.save_form_d_complete(
                    form_d, sec_filing_id=row["secFilingId"]
                )
                if ok:
                    parsed += 1
            except Exception as e:
                logger.warning(
                    f"Failed to parse Form D {row['accessionNumber']}: {e}"
                )
        logger.info(f"Parsed {parsed}/{len(unparsed)} Form D filings")
        return parsed
