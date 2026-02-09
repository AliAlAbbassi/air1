import asyncio

from loguru import logger

from air1.config import settings
from air1.db.prisma_client import disconnect_db
from air1.services.ingest.service import Service


async def sec_edgar_ingest(
    enrich_batch_size: int = 500,
    enrich_iterations: int = 25,
    form_d_days: int = 30,
    form_d_parse_batch: int = 100,
    form_d_parse_iterations: int = 20,
):
    """
    Full SEC EDGAR ingestion pipeline.

    1. Bootstrap: download all ~10K public company tickers
    2. Enrich: fetch company details (SIC, address, phone, website) in batches
    3. Form D index: fetch recent Form D filings
    4. Form D parse: extract issuer/offering/officer data + auto-create companies
    """
    try:
        async with Service(identity=settings.sec_edgar_identity) as svc:
            # Step 1: Bootstrap companies
            company_count = await svc.bootstrap_companies()
            logger.info(f"Bootstrap complete: {company_count} companies")

            # Step 2: Enrich in batches
            total_enriched = 0
            for _ in range(enrich_iterations):
                enriched = await svc.enrich_companies(batch_size=enrich_batch_size)
                total_enriched += enriched
                if enriched < enrich_batch_size:
                    break
            logger.info(f"Enrichment complete: {total_enriched} companies enriched")

            # Step 3: Fetch Form D filing index
            form_d_count = await svc.ingest_form_d_filings(days=form_d_days)
            logger.info(f"Form D index complete: {form_d_count} filings")

            # Step 4: Parse Form D details in batches (auto-creates companies from issuer data)
            total_parsed = 0
            for _ in range(form_d_parse_iterations):
                parsed = await svc.parse_form_d_details(batch_size=form_d_parse_batch)
                total_parsed += parsed
                if parsed < form_d_parse_batch:
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


async def sec_edgar_daily(
    form_d_parse_batch: int = 100,
    form_d_parse_iterations: int = 50,
    date_str: str | None = None,
):
    """
    Daily SEC EDGAR pipeline - lightweight version for daily runs.

    1. Fetch yesterday's Form D filings via daily index
    2. Parse all unparsed Form D filings (auto-creates companies)
    """
    try:
        async with Service(identity=settings.sec_edgar_identity) as svc:
            # Step 1: Fetch daily Form D index
            form_d_count = await svc.ingest_daily_form_d(date_str=date_str)
            logger.info(f"Daily Form D index: {form_d_count} filings")

            # Step 2: Parse all unparsed
            total_parsed = 0
            for _ in range(form_d_parse_iterations):
                parsed = await svc.parse_form_d_details(batch_size=form_d_parse_batch)
                total_parsed += parsed
                if parsed < form_d_parse_batch:
                    break
            logger.info(f"Form D parsing complete: {total_parsed} filings parsed")

            return {
                "form_d_indexed": form_d_count,
                "form_d_parsed": total_parsed,
            }
    finally:
        await disconnect_db()


if __name__ == "__main__":
    result = asyncio.run(sec_edgar_ingest())
    logger.info(f"Pipeline complete: {result}")
