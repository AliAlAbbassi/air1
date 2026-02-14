"""Prefect flows for SEC EDGAR ingestion pipeline.

DAG structure for full pipeline:

    bootstrap ──┬──→ enrich (batched)
                └──→ index ──→ parse (batched)

Enrich and index run in parallel after bootstrap.
Parse waits for index to complete.
"""

import asyncio
from typing import Optional

from loguru import logger
from prefect import flow, task

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.ingest.service import Service


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(retries=2, retry_delay_seconds=60, log_prints=True)
async def bootstrap_companies_task() -> int:
    """Download and store all public companies from SEC."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.bootstrap_companies()


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def enrich_companies_task(
    batch_size: int = 500, max_iterations: int = 25
) -> int:
    """Enrich unenriched companies in batches until done."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        total = 0
        for _ in range(max_iterations):
            enriched = await svc.enrich_companies(batch_size=batch_size)
            total += enriched
            if enriched < batch_size:
                break
        return total


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
async def ingest_daily_form_d_task(date_str: Optional[str] = None) -> int:
    """Fetch Form D filings for a single day using the daily index."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.ingest_daily_form_d(date_str=date_str)


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def ingest_current_form_d_task() -> int:
    """Fetch real-time Form D filings from SEC current feed."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        return await svc.ingest_current_form_d()


@task(retries=1, retry_delay_seconds=30, log_prints=True)
async def parse_form_d_task(
    batch_size: int = 100, max_iterations: int = 50
) -> int:
    """Parse all unparsed Form D filings in batches until done."""
    async with Service(identity=settings.sec_edgar_identity) as svc:
        total = 0
        for _ in range(max_iterations):
            parsed = await svc.parse_form_d_details(batch_size=batch_size)
            total += parsed
            if parsed < batch_size:
                break
        return total


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------


@flow(name="sec-edgar-full-ingest", log_prints=True)
async def full_ingest_flow(
    enrich_batch_size: int = 500,
    enrich_iterations: int = 25,
    form_d_days: int = 30,
    form_d_parse_batch: int = 100,
    parse_iterations: int = 50,
):
    """Full SEC EDGAR ingestion pipeline (DAG).

    bootstrap ──┬──→ enrich
                └──→ index ──→ parse

    Enrich and index run in parallel after bootstrap.
    """
    try:
        # Step 1: Bootstrap (must complete before anything else)
        company_count = await bootstrap_companies_task()
        logger.info(f"Bootstrap complete: {company_count} companies")

        # Step 2+3: Enrich and Index run in parallel
        enrich_coro = enrich_companies_task(
            batch_size=enrich_batch_size, max_iterations=enrich_iterations
        )
        index_coro = ingest_form_d_index_task(days=form_d_days)

        total_enriched, form_d_count = await asyncio.gather(
            enrich_coro, index_coro
        )
        logger.info(f"Enrich complete: {total_enriched} companies")
        logger.info(f"Form D index complete: {form_d_count} filings")

        # Step 4: Parse (depends on index completing)
        total_parsed = await parse_form_d_task(
            batch_size=form_d_parse_batch, max_iterations=parse_iterations
        )
        logger.info(f"Form D parse complete: {total_parsed} filings")

        return {
            "companies_bootstrapped": company_count,
            "companies_enriched": total_enriched,
            "form_d_indexed": form_d_count,
            "form_d_parsed": total_parsed,
        }
    finally:
        await disconnect_db()


@flow(name="sec-form-d-daily", log_prints=True)
async def form_d_daily_flow(
    parse_batch: int = 100,
    parse_iterations: int = 50,
    date_str: Optional[str] = None,
):
    """Daily Form D pipeline: fetch yesterday's index + parse all unparsed."""
    try:
        indexed = await ingest_daily_form_d_task(date_str=date_str)
        logger.info(f"Daily index complete: {indexed} filings")

        total_parsed = await parse_form_d_task(
            batch_size=parse_batch, max_iterations=parse_iterations
        )
        logger.info(f"Parse complete: {total_parsed} filings")

        return {"form_d_indexed": indexed, "form_d_parsed": total_parsed}
    finally:
        await disconnect_db()


@flow(name="sec-form-d-ingest", log_prints=True)
async def form_d_flow(
    days: int = 30,
    parse_batch: int = 100,
    parse_iterations: int = 50,
):
    """Fetch and parse Form D filings."""
    try:
        indexed = await ingest_form_d_index_task(days=days)
        logger.info(f"Index complete: {indexed} filings")

        total_parsed = await parse_form_d_task(
            batch_size=parse_batch, max_iterations=parse_iterations
        )
        logger.info(f"Parse complete: {total_parsed} filings")

        return {"form_d_indexed": indexed, "form_d_parsed": total_parsed}
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
    """Enrich companies incrementally."""
    try:
        total = await enrich_companies_task(
            batch_size=batch_size, max_iterations=iterations
        )
        return {"companies_enriched": total}
    finally:
        await disconnect_db()
