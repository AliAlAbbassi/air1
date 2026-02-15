"""Database repository for the leadgen service."""

import json
from typing import Any, Optional

from loguru import logger

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import leadgen_queries


async def get_software_product(slug: str) -> Optional[dict]:
    """Get a software product by slug."""
    db = await get_prisma()
    return await leadgen_queries.get_software_product_by_slug(db, slug=slug)


async def upsert_software_product(
    name: str, slug: str, website: Optional[str], detection_patterns: dict
) -> dict:
    """Insert or update a software product."""
    db = await get_prisma()
    return await leadgen_queries.insert_software_product(
        db,
        name=name,
        slug=slug,
        website=website,
        detection_patterns=json.dumps(detection_patterns),
    )


async def create_lead_search(
    software_product_id: int,
    search_params: dict,
    user_id: Optional[str] = None,
) -> int:
    """Create a lead search and return its ID."""
    db = await get_prisma()
    result = await leadgen_queries.insert_lead_search(
        db,
        user_id=user_id,
        software_product_id=software_product_id,
        search_params=json.dumps(search_params),
        status="pending",
    )
    return result["id"]


async def update_search_status(search_id: int, status: str, stats: dict = None):
    """Update the status and stats of a lead search."""
    db = await get_prisma()
    await leadgen_queries.update_lead_search_status(
        db,
        search_id=search_id,
        status=status,
        stats=json.dumps(stats or {}),
    )


async def get_lead_search(search_id: int) -> Optional[dict]:
    """Get a lead search by ID."""
    db = await get_prisma()
    return await leadgen_queries.get_lead_search(db, search_id=search_id)


async def get_software_product_by_id(product_id: int) -> Optional[dict]:
    """Get a software product by ID."""
    db = await get_prisma()
    return await leadgen_queries.get_software_product_by_id(db, product_id=product_id)


async def batch_insert_leads(
    search_id: int, leads: list[dict]
) -> int:
    """Batch insert discovered leads into search_leads.

    Uses the VALUES batch pattern for efficiency.
    Returns number of rows inserted.
    """
    if not leads:
        return 0

    db = await get_prisma()

    # Build batch INSERT with VALUES
    values_parts = []
    params: list[Any] = []
    idx = 1

    for lead in leads:
        placeholders = ", ".join(f"${idx + i}" for i in range(12))
        values_parts.append(f"({placeholders})")

        params.extend([
            search_id,
            lead.get("name", ""),
            lead.get("website"),
            lead.get("phone"),
            lead.get("email"),
            lead.get("address"),
            lead.get("city"),
            lead.get("state"),
            lead.get("country"),
            lead.get("latitude"),
            lead.get("longitude"),
            lead.get("google_place_id"),
        ])
        idx += 12

    sql = f"""
        INSERT INTO search_leads
            (lead_search_id, name, website, phone, email, address,
             city, state, country, latitude, longitude, google_place_id,
             source, detection_status)
        VALUES {", ".join(values_parts)}
        ON CONFLICT DO NOTHING
    """

    # Add source and detection_status as literal values in the SQL
    # Actually, let's include them in the params
    # Rebuild with 14 params per row
    values_parts = []
    params = []
    idx = 1

    for lead in leads:
        placeholders = ", ".join(f"${idx + i}" for i in range(14))
        values_parts.append(f"({placeholders})")

        params.extend([
            search_id,
            lead.get("name", ""),
            lead.get("website"),
            lead.get("phone"),
            lead.get("email"),
            lead.get("address"),
            lead.get("city"),
            lead.get("state"),
            lead.get("country"),
            lead.get("latitude"),
            lead.get("longitude"),
            lead.get("google_place_id"),
            lead.get("source", "serper_maps"),
            "pending",
        ])
        idx += 14

    sql = f"""
        INSERT INTO search_leads
            (lead_search_id, name, website, phone, email, address,
             city, state, country, latitude, longitude, google_place_id,
             source, detection_status)
        VALUES {", ".join(values_parts)}
    """

    await db.query_raw(sql, *params)
    logger.info(f"Inserted {len(leads)} leads for search {search_id}")
    return len(leads)


async def get_pending_leads(search_id: int) -> list[dict]:
    """Get leads pending detection (have a website)."""
    db = await get_prisma()
    return await leadgen_queries.get_pending_leads(db, search_id=search_id)


async def update_lead_detection(
    lead_id: int,
    detection_status: str,
    detected_software: Optional[str] = None,
    detection_method: Optional[str] = None,
    detection_details: Optional[dict] = None,
):
    """Update detection results for a lead."""
    db = await get_prisma()
    await leadgen_queries.update_lead_detection(
        db,
        lead_id=lead_id,
        detection_status=detection_status,
        detected_software=detected_software,
        detection_method=detection_method,
        detection_details=json.dumps(detection_details or {}),
    )


async def get_search_results(search_id: int) -> list[dict]:
    """Get all results for a search."""
    db = await get_prisma()
    return await leadgen_queries.get_search_results(db, search_id=search_id)


async def get_detected_leads(search_id: int) -> list[dict]:
    """Get only detected leads for a search."""
    db = await get_prisma()
    return await leadgen_queries.get_detected_leads(db, search_id=search_id)
