"""Check companies without websites."""

import asyncio

from air1.db.prisma_client import get_prisma, disconnect_db


async def main():
    p = await get_prisma()

    # Count companies without websites
    count = await p.query_raw(
        """
        SELECT COUNT(*) as c
        FROM sec_company
        WHERE website IS NULL
        """
    )
    print(f"Companies without websites: {count[0]['c']}")

    # Show some examples
    rows = await p.query_raw(
        """
        SELECT cik, name, ticker
        FROM sec_company
        WHERE website IS NULL
        ORDER BY created_on DESC
        LIMIT 10
        """
    )
    print("\nExamples:")
    for r in rows:
        print(f"  {r['name']} (CIK: {r['cik']}, Ticker: {r['ticker']})")

    # Count companies WITH websites
    with_count = await p.query_raw(
        """
        SELECT COUNT(*) as c
        FROM sec_company
        WHERE website IS NOT NULL
        """
    )
    print(f"\nCompanies WITH websites: {with_count[0]['c']}")

    # Show examples with websites
    with_rows = await p.query_raw(
        """
        SELECT cik, name, website
        FROM sec_company
        WHERE website IS NOT NULL
        ORDER BY created_on DESC
        LIMIT 5
        """
    )
    print("\nExamples with websites:")
    for r in with_rows:
        print(f"  {r['name']}: {r['website']}")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
