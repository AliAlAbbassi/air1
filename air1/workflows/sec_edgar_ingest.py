"""SEC EDGAR ingestion workflow entrypoints.

These invoke the Prefect flows from flows.py.
Prefect flows work with or without a Prefect server — without one,
they run as normal async functions (no retries/dashboard).

Usage:
    python air1/workflows/sec_edgar_ingest.py full
    python air1/workflows/sec_edgar_ingest.py daily [YYYY-MM-DD]
    python air1/workflows/sec_edgar_ingest.py form-d [days]
    python air1/workflows/sec_edgar_ingest.py bootstrap
    python air1/workflows/sec_edgar_ingest.py enrich
"""

import asyncio
import sys

from loguru import logger

from air1.services.ingest.flows import (
    bootstrap_flow,
    enrich_flow,
    form_d_daily_flow,
    form_d_flow,
    full_ingest_flow,
)

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "full"

    if command == "full":
        result = asyncio.run(full_ingest_flow())
    elif command == "daily":
        date_str = sys.argv[2] if len(sys.argv) > 2 else None
        result = asyncio.run(form_d_daily_flow(date_str=date_str))
    elif command == "form-d":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        result = asyncio.run(form_d_flow(days=days))
    elif command == "bootstrap":
        result = asyncio.run(bootstrap_flow())
    elif command == "enrich":
        result = asyncio.run(enrich_flow())
    else:
        print("Usage: python air1/workflows/sec_edgar_ingest.py [full|daily|form-d|bootstrap|enrich]")
        sys.exit(1)

    logger.info(f"Pipeline complete: {result}")
