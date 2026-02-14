# Deduplicate link_orphaned_filings calls

**Priority:** Low
**Estimated speedup:** Minor (removes redundant full-table UPDATE)

## Problem

`link_orphaned_filings` is called in two places during a single parse cycle:

1. Inside `upsert_filings_batch` (repo.py:232) — after every filing chunk store
2. At the end of `parse_form_d_details` (service.py:231) — after all writes

The call inside `upsert_filings_batch` is wasteful because companies haven't been created from issuer data yet at that point — the orphan linking only becomes meaningful after `upsert_company_from_issuer` runs during the parse phase.

## Fix

Remove `link_orphaned_filings` from `upsert_filings_batch`. Keep it only at the end of `parse_form_d_details` (or at the end of the flow).

## Files

- `air1/services/ingest/repo.py` — remove `link_orphaned_filings` call from `upsert_filings_batch`
