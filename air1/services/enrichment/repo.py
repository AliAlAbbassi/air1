"""Database repository for company enrichment operations."""

from loguru import logger

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import enrichment_queries as queries


async def get_companies_without_websites(limit: int = 100) -> list[dict]:
    """Get Form D software/tech startup companies without websites."""
    p = await get_prisma()
    return await queries.get_software_companies_without_websites(p, limit=limit)


async def update_companies_enrichment_batch(
    updates: list[tuple[str, str | None, str | None, str | None]]
) -> int:
    """Batch update company website, linkedin_url, and twitter_url.

    Args:
        updates: List of (cik, website, linkedin_url, twitter_url) tuples

    Returns:
        Number of companies updated
    """
    if not updates:
        return 0

    p = await get_prisma()

    try:
        chunk_size = 500  # 4 params per row = 2000 params max
        total_updated = 0

        for i in range(0, len(updates), chunk_size):
            chunk = updates[i : i + chunk_size]
            values_placeholders = []
            params = []

            for idx, (cik, website, linkedin, twitter) in enumerate(chunk):
                base = idx * 4 + 1
                values_placeholders.append(
                    f"(${base}, ${base + 1}, ${base + 2}, ${base + 3})"
                )
                params.extend([cik, website or "", linkedin or "", twitter or ""])

            values_clause = ", ".join(values_placeholders)
            sql = f"""
                UPDATE sec_company SET
                    website = CASE WHEN v.website != '' THEN v.website ELSE sec_company.website END,
                    linkedin_url = CASE WHEN v.linkedin != '' THEN v.linkedin ELSE sec_company.linkedin_url END,
                    twitter_url = CASE WHEN v.twitter != '' THEN v.twitter ELSE sec_company.twitter_url END,
                    updated_on = NOW()
                FROM (VALUES {values_clause}) AS v(cik, website, linkedin, twitter)
                WHERE sec_company.cik = v.cik
            """

            result = await p.execute_raw(sql, *params)
            total_updated += result

        return total_updated

    except Exception as e:
        logger.error(f"Database error batch updating enrichment: {e}")
        return 0
