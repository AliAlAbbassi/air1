# Batch bootstrap_companies INSERT

**Priority:** High
**Estimated speedup:** ~10x (14s -> ~1s)

## Problem

`repo.upsert_companies_batch()` loops through 10,532 companies one at a time, each executing a separate INSERT query. This takes ~14 seconds.

```python
# repo.py:50-57
async def upsert_companies_batch(companies: list[SecCompanyData]) -> int:
    success_count = 0
    for company in companies:
        ok, _ = await upsert_company(company)  # 10,532 individual queries
        if ok:
            success_count += 1
    return success_count
```

## Fix

Replace with a multi-row INSERT like `upsert_filings_batch` already does. Chunk at 1000 rows (4 params each = 4000 params, well under Postgres 32K limit).

```python
async def upsert_companies_batch(companies: list[SecCompanyData]) -> int:
    if not companies:
        return 0
    chunk_size = 1000
    total = 0
    for i in range(0, len(companies), chunk_size):
        chunk = companies[i : i + chunk_size]
        # Build multi-row VALUES for single INSERT
        # (cik, name, ticker, exchange) per row
        ...
        await prisma.execute_raw(sql, *params)
        total += len(chunk)
    return total
```

## Files

- `air1/services/ingest/repo.py` — rewrite `upsert_companies_batch`
