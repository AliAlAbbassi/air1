"""Database repository for company enrichment operations."""

from typing import Optional
from loguru import logger

from air1.db.prisma_client import get_prisma


async def get_companies_without_websites(limit: int = 100) -> list[dict]:
    """Get Form D tech/software startup companies without websites.

    Filters out funds and non-tech companies, only returns companies that
    have actually sold capital (total_amount_sold > 0).

    Returns list of dicts with cik, name, city, state.
    """
    p = await get_prisma()
    results = await p.query_raw(
        """
        SELECT DISTINCT
            sc.cik,
            sfd.issuer_name as name,
            sfd.issuer_city as city,
            sfd.issuer_state as state,
            sfd.industry_group_type,
            sfd.total_offering_amount,
            sfd.total_amount_sold
        FROM sec_company sc
        JOIN sec_filing sf ON sf.cik = sc.cik
        JOIN sec_form_d sfd ON sfd.sec_filing_id = sf.sec_filing_id
        WHERE sfd.is_pooled_investment = false
          AND sfd.industry_group_type NOT IN (
            'Pooled Investment Fund', 'Investing', 'REITS and Finance',
            'Other Banking and Financial Services', 'Insurance',
            'Investment Banking', 'Commercial Banking'
          )
          AND sfd.issuer_name NOT ILIKE '%fund%'
          AND sfd.issuer_name NOT ILIKE '%investment%'
          AND sfd.issuer_name NOT ILIKE '%holdings%'
          AND sfd.issuer_name NOT ILIKE '%investor%'
          AND sfd.total_amount_sold > 0
          AND (sc.website IS NULL OR sc.website = '')
        ORDER BY sf.filing_date DESC
        LIMIT $1
        """,
        limit,
    )
    return results


async def update_company_website(cik: str, website: str) -> bool:
    """Update a company's website.

    Args:
        cik: Company CIK
        website: Website URL

    Returns:
        True if updated, False otherwise
    """
    p = await get_prisma()
    try:
        result = await p.execute_raw(
            """
            UPDATE sec_company
            SET website = $1, updated_on = NOW()
            WHERE cik = $2
            """,
            website,
            cik,
        )
        return result > 0
    except Exception as e:
        logger.error(f"Failed to update website for CIK {cik}: {e}")
        return False


async def update_companies_websites_batch(updates: list[tuple[str, str]]) -> int:
    """Batch update company websites.

    Args:
        updates: List of (cik, website) tuples

    Returns:
        Number of companies updated
    """
    if not updates:
        return 0

    p = await get_prisma()

    try:
        # Build VALUES clause: (cik1, website1), (cik2, website2), ...
        # Each row: 2 params
        chunk_size = 1000  # 2000 params total, well under 32K limit
        total_updated = 0

        for i in range(0, len(updates), chunk_size):
            chunk = updates[i : i + chunk_size]
            values_placeholders = []
            params = []

            for idx, (cik, website) in enumerate(chunk):
                base = idx * 2 + 1
                values_placeholders.append(f"($${base}, $${base + 1})")
                params.extend([cik, website])

            values_clause = ", ".join(values_placeholders)
            sql = f"""
                UPDATE sec_company SET
                    website = v.website,
                    updated_on = NOW()
                FROM (VALUES {values_clause}) AS v(cik, website)
                WHERE sec_company.cik = v.cik
            """

            result = await p.execute_raw(sql, *params)
            total_updated += result

        return total_updated

    except Exception as e:
        logger.error(f"Database error batch updating websites: {e}")
        return 0
