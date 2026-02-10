"""SEC EDGAR ingestion workflow entrypoints.

These are thin wrappers that invoke the Prefect flows from flows.py.
Prefect flows work with or without a Prefect server — without one,
they run as normal async functions (no retries/dashboard).
"""

import asyncio
import sys

from loguru import logger

from air1.services.ingest.flows import (
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
    else:
        print(f"Usage: python -m air1.workflows.sec_edgar_ingest [full|daily|form-d]")
        sys.exit(1)

    logger.info(f"Pipeline complete: {result}")
