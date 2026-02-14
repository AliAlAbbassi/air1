# Batch enrich_companies DB writes

**Priority:** Medium
**Estimated speedup:** ~5x (500 UPDATEs -> 1 query)

## Problem

`enrich_companies` fetches profiles concurrently (good) but writes each enrichment as an individual UPDATE. 500 companies = 500 DB round-trips.

```python
# service.py:103-110
async def _enrich_one(row: dict) -> bool:
    async with sem:
        profile = await self._client.fetch_company_profile(row["cik"])
        return await repo.enrich_company(profile)  # 1 UPDATE per company
```

## Fix

Collect all successful profiles from the concurrent fetch phase, then batch-update in a single query using `UPDATE ... FROM (VALUES ...)`:

```sql
UPDATE sec_company SET
    sic = v.sic, sic_description = v.sic_description, ...
    enriched_at = NOW(), updated_on = NOW()
FROM (VALUES
    ($1, $2, $3, ...),
    ($4, $5, $6, ...),
    ...
) AS v(cik, sic, sic_description, ...)
WHERE sec_company.cik = v.cik;
```

Same two-phase pattern as parse: concurrent API fetch, then single batch DB write.

## Files

- `air1/services/ingest/repo.py` — add `enrich_companies_batch()`
- `air1/services/ingest/service.py` — restructure `enrich_companies` to collect profiles then batch-write
