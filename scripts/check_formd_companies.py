"""Check Form D companies for website enrichment."""

import asyncio

from air1.db.prisma_client import get_prisma, disconnect_db


async def main():
    p = await get_prisma()

    # Get Form D issuers that are actual startups (not funds)
    rows = await p.query_raw(
        """
        SELECT
            sc.cik,
            sc.name,
            sc.website,
            sc.city,
            sc.state_or_country as state,
            sfd.industry_group_type,
            sfd.issuer_name
        FROM sec_company sc
        INNER JOIN sec_filing sf ON sf.cik = sc.cik
        INNER JOIN sec_form_d sfd ON sfd.sec_filing_id = sf.sec_filing_id
        WHERE sfd.is_pooled_investment = false
          AND sfd.industry_group_type NOT IN (
            'Pooled Investment Fund', 'Investing', 'REITS and Finance',
            'Other Banking and Financial Services', 'Insurance',
            'Investment Banking', 'Commercial Banking'
          )
          AND (sc.website IS NULL OR sc.website = '')
        ORDER BY sc.created_on DESC
        LIMIT 20
        """
    )

    print(f"Form D startup companies without websites (first 20):\n")
    for r in rows:
        location = f"{r['city']}, {r['state']}" if r['city'] and r['state'] else ''
        print(f"  {r['issuer_name'] or r['name']}")
        print(f"    CIK: {r['cik']}, Industry: {r['industry_group_type']}")
        print(f"    {location}\n")

    # Count total
    count = await p.query_raw(
        """
        SELECT COUNT(DISTINCT sc.cik) as c
        FROM sec_company sc
        INNER JOIN sec_filing sf ON sf.cik = sc.cik
        INNER JOIN sec_form_d sfd ON sfd.sec_filing_id = sf.sec_filing_id
        WHERE sfd.is_pooled_investment = false
          AND sfd.industry_group_type NOT IN (
            'Pooled Investment Fund', 'Investing', 'REITS and Finance',
            'Other Banking and Financial Services', 'Insurance',
            'Investment Banking', 'Commercial Banking'
          )
          AND (sc.website IS NULL OR sc.website = '')
        """
    )

    print(f"\nTotal startup companies without websites: {count[0]['c']}")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
