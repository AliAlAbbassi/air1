"""SEC EDGAR ingestion service.

Orchestrates SEC EDGAR data fetching and database persistence.
Uses edgartools for API access and the repo layer for storage.
"""

import asyncio
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
    async def ingest_daily_form_d(self, date_str: Optional[str] = None) -> int:
        """Ingest Form D filings for a single day using the daily index."""
        ...

    @abstractmethod
    async def ingest_current_form_d(self) -> int:
        """Ingest real-time Form D filings from SEC current feed."""
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

    async def enrich_companies(
        self, batch_size: int = 500, concurrency: int = 8
    ) -> int:
        """Fetch SEC profiles for unenriched companies.

        Processes one batch with concurrent requests (default 8, under
        SEC's 10 req/s limit). Call repeatedly to enrich all.
        Returns count of successfully enriched companies.
        """
        unenriched = await repo.get_companies_not_enriched(limit=batch_size)
        if not unenriched:
            logger.info("No unenriched companies remaining")
            return 0

        logger.info(f"Enriching {len(unenriched)} companies ({concurrency} concurrent)...")
        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(row: dict):
            async with sem:
                try:
                    return await self._client.fetch_company_profile(row["cik"])
                except Exception as e:
                    logger.warning(f"Failed to enrich CIK={row['cik']}: {e}")
                    return None

        results = await asyncio.gather(*[_fetch_one(r) for r in unenriched])
        profiles = [p for p in results if p is not None]
        enriched = await repo.enrich_companies_batch(profiles)
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
        return await self._store_filings(filings)

    async def ingest_daily_form_d(self, date_str: Optional[str] = None) -> int:
        """Ingest Form D filings for a single day using the daily index (efficient).

        Args:
            date_str: Date in YYYY-MM-DD format. Defaults to yesterday.
        """
        filings = await self._client.fetch_daily_form_d_filings(date_str)
        return await self._store_filings(filings)

    async def ingest_current_form_d(self) -> int:
        """Ingest real-time Form D filings from SEC current feed (~24 hours)."""
        filings = await self._client.fetch_current_form_d_filings()
        return await self._store_filings(filings)

    async def _store_filings(self, filings: list) -> int:
        """Store a list of SecFilingData in batch (single SQL query per chunk)."""
        if not filings:
            return 0

        # Postgres has a parameter limit (~32K), chunk at 1000 filings (5 params each)
        chunk_size = 1000
        stored = 0
        for i in range(0, len(filings), chunk_size):
            chunk = filings[i : i + chunk_size]
            stored += await repo.upsert_filings_batch(chunk)
        logger.info(f"Stored {stored}/{len(filings)} Form D filings")
        return stored

    async def parse_form_d_details(
        self, batch_size: int = 100, concurrency: int = 8
    ) -> int:
        """Parse unparsed Form D filings to extract issuer, offering, and officers.

        Fetches Form D XML from SEC concurrently (up to `concurrency`), then
        writes to DB sequentially (transactions require serial access).
        Auto-creates sec_company records from issuer data for private companies.

        Returns count of successfully parsed filings.
        """
        unparsed = await repo.get_form_d_filings_not_parsed(limit=batch_size)
        if not unparsed:
            logger.info("No unparsed Form D filings remaining")
            return 0

        logger.info(f"Parsing {len(unparsed)} Form D filings ({concurrency} concurrent fetches)...")

        # Step 1: Fetch all Form D details concurrently from SEC API
        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(row: dict):
            async with sem:
                try:
                    form_d = await self._client.fetch_form_d_detail(
                        row["accessionNumber"]
                    )
                    return (row, form_d)
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch Form D {row['accessionNumber']}: {e}"
                    )
                    return (row, None)

        fetch_results = await asyncio.gather(*[_fetch_one(r) for r in unparsed])

        # Step 2: Collect valid results and batch-write to DB
        issuers: dict[str, tuple] = {}
        form_d_items: list[tuple] = []  # (SecFormDData, sec_filing_id)
        for row, form_d in fetch_results:
            if form_d is None:
                continue
            if form_d.issuer_name and form_d.cik not in issuers:
                issuers[form_d.cik] = (
                    form_d.cik,
                    form_d.issuer_name,
                    form_d.issuer_street,
                    form_d.issuer_city,
                    form_d.issuer_state,
                    form_d.issuer_zip,
                    form_d.issuer_phone,
                )
            form_d_items.append((form_d, row["secFilingId"]))

        # Batch upsert issuer companies first (needed for FK linkage)
        if issuers:
            await repo.upsert_companies_from_issuers_batch(list(issuers.values()))

        # Batch save all form_d + officers in a single transaction
        parsed = await repo.save_form_d_batch(form_d_items)

        # Link any filings that were orphaned before the company was created
        await repo.link_orphaned_filings()

        logger.info(f"Parsed {parsed}/{len(unparsed)} Form D filings")
        return parsed
