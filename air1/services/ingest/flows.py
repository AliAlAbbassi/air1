"""Prefect flows for SEC EDGAR ingestion pipeline.

Flows orchestrate the service methods with retries, logging, and scheduling.
The service works standalone (via CLI) without Prefect — these flows add
orchestration on top.
"""

from typing import Optional

from loguru import logger
from prefect import flow, task

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.ingest.service import Service


@task(retries=2, retry_delay_seconds=60, log_prints=True)
async def bootstrap_companies_task() -> int:
    """Download and store all public companies from SEC."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.bootstrap_companies()


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def enrich_companies_task(batch_size: int = 500) -> int:
    """Enrich a batch of unenriched companies."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.enrich_companies(batch_size=batch_size)


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def ingest_form_d_index_task(
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    days: int = 30,
) -> int:
    """Fetch Form D filing index for a date range."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.ingest_form_d_filings(
            date_start=date_start, date_end=date_end, days=days
        )


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def parse_form_d_batch_task(batch_size: int = 100) -> int:
    """Parse a batch of unparsed Form D filings."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.parse_form_d_details(batch_size=batch_size)


@flow(name="sec-edgar-full-ingest", log_prints=True)
async def full_ingest_flow(
    enrich_batch_size: int = 500,
    form_d_days: int = 30,
    form_d_parse_batch: int = 100,
    enrich_iterations: int = 25,
    parse_iterations: int = 20,
):
    """Full SEC EDGAR ingestion pipeline.

    1. Bootstrap: download all company tickers
    2. Enrich: fetch company details in batches
    3. Form D index: fetch recent Form D filings
    4. Form D parse: extract issuer/offering/officer data
    """
    try:
        # Step 1: Bootstrap
        company_count = await bootstrap_companies_task()
        logger.info(f"Bootstrap complete: {company_count} companies")

        # Step 2: Enrich in batches
        total_enriched = 0
        for i in range(enrich_iterations):
            enriched = await enrich_companies_task(batch_size=enrich_batch_size)
            total_enriched += enriched
            if enriched < enrich_batch_size:
                logger.info("All companies enriched")
                break
        logger.info(f"Enrichment complete: {total_enriched} companies enriched")

        # Step 3: Fetch Form D filing index
        form_d_count = await ingest_form_d_index_task(days=form_d_days)
        logger.info(f"Form D index complete: {form_d_count} filings")

        # Step 4: Parse Form D details in batches
        total_parsed = 0
        for i in range(parse_iterations):
            parsed = await parse_form_d_batch_task(batch_size=form_d_parse_batch)
            total_parsed += parsed
            if parsed < form_d_parse_batch:
                logger.info("All Form D filings parsed")
                break
        logger.info(f"Form D parsing complete: {total_parsed} filings parsed")

        return {
            "companies_bootstrapped": company_count,
            "companies_enriched": total_enriched,
            "form_d_indexed": form_d_count,
            "form_d_parsed": total_parsed,
        }
    finally:
        await disconnect_db()


@flow(name="sec-edgar-bootstrap", log_prints=True)
async def bootstrap_flow():
    """Just bootstrap companies (fast, one-shot)."""
    try:
        count = await bootstrap_companies_task()
        return {"companies_bootstrapped": count}
    finally:
        await disconnect_db()


@flow(name="sec-edgar-enrich", log_prints=True)
async def enrich_flow(batch_size: int = 500, iterations: int = 25):
    """Enrich companies incrementally in batches."""
    try:
        total = 0
        for i in range(iterations):
            enriched = await enrich_companies_task(batch_size=batch_size)
            total += enriched
            if enriched < batch_size:
                break
        return {"companies_enriched": total}
    finally:
        await disconnect_db()


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def ingest_daily_form_d_task(date_str: Optional[str] = None) -> int:
    """Fetch Form D filings for a single day using the daily index."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.ingest_daily_form_d(date_str=date_str)


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def ingest_current_form_d_task() -> int:
    """Fetch real-time Form D filings from SEC current feed."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.ingest_current_form_d()


@flow(name="sec-form-d-daily", log_prints=True)
async def form_d_daily_flow(
    parse_batch: int = 100,
    parse_iterations: int = 50,
    date_str: Optional[str] = None,
):
    """Daily Form D pipeline: fetch yesterday's index + parse all unparsed."""
    try:
        indexed = await ingest_daily_form_d_task(date_str=date_str)
        total_parsed = 0
        for i in range(parse_iterations):
            parsed = await parse_form_d_batch_task(batch_size=parse_batch)
            total_parsed += parsed
            if parsed < parse_batch:
                break
        return {"form_d_indexed": indexed, "form_d_parsed": total_parsed}
    finally:
        await disconnect_db()


@flow(name="sec-form-d-ingest", log_prints=True)
async def form_d_flow(
    days: int = 30,
    parse_batch: int = 100,
    parse_iterations: int = 20,
):
    """Fetch and parse Form D filings."""
    try:
        indexed = await ingest_form_d_index_task(days=days)
        total_parsed = 0
        for i in range(parse_iterations):
            parsed = await parse_form_d_batch_task(batch_size=parse_batch)
            total_parsed += parsed
            if parsed < parse_batch:
                break
        return {"form_d_indexed": indexed, "form_d_parsed": total_parsed}
    finally:
        await disconnect_db()
