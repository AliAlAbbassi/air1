# Batch save_form_d_complete

**Priority:** High
**Estimated speedup:** ~10x (~600 queries -> 2 queries per batch)

## Problem

`repo.save_form_d_complete()` runs N+4 queries per filing (BEGIN, upsert form_d, delete officers, N officer INSERTs, COMMIT). For a batch of 100 filings with ~3 officers each, that's ~600 sequential DB round-trips.

```python
# repo.py:276-329 — per filing:
await prisma.query_raw("BEGIN")
form_d_result = await queries.upsert_sec_form_d(...)       # 1 query
await queries.delete_officers_by_form_d(...)                # 1 query
for officer in form_d.officers:
    await queries.insert_sec_officer(...)                   # N queries (~3 avg)
await prisma.query_raw("COMMIT")
```

## Fix

Batch the entire write phase:

1. One multi-row INSERT for all form_d records (100 rows)
2. One DELETE for all officers of those form_d IDs
3. One multi-row INSERT for all officers (~300 rows)
4. Wrap in a single BEGIN/COMMIT

This replaces `save_form_d_complete` with a new `save_form_d_batch` that takes the full list of (form_d, sec_filing_id) pairs.

## Files

- `air1/services/ingest/repo.py` — add `save_form_d_batch()`
- `air1/services/ingest/service.py` — update `parse_form_d_details` step 2 to call batch method
- `air1/db/query/sec_form_d.sql` — may need batch-compatible query
- `air1/db/query/sec_officer.sql` — may need batch-compatible query
