"""Check what company names we're trying to enrich."""

import asyncio

from air1.db.prisma_client import get_prisma, disconnect_db


async def main():
    p = await get_prisma()

    # Get companies without websites
    rows = await p.query_raw(
        """
        SELECT cik, name, ticker, city, state_or_country as state
        FROM sec_company
        WHERE website IS NULL OR website = ''
        ORDER BY created_on DESC
        LIMIT 20
        """
    )
    print(f"Companies without websites (first 20):\n")
    for r in rows:
        location = f"{r['city']}, {r['state']}" if r['city'] and r['state'] else ''
        print(f"  {r['name']}")
        print(f"    CIK: {r['cik']}, Ticker: {r['ticker']}, {location}\n")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
