# Batch issuer company upsert during parse

**Priority:** Medium
**Estimated speedup:** ~3x (100 queries -> 1 query)

## Problem

During `parse_form_d_details`, each filing calls `repo.upsert_company_from_issuer()` individually in the sequential DB write loop. 100 filings = 100 extra INSERT queries.

```python
# service.py:210-218
for row, form_d in fetch_results:
    if form_d.issuer_name:
        await repo.upsert_company_from_issuer(  # 1 query per filing
            cik=form_d.cik,
            name=form_d.issuer_name,
            ...
        )
```

## Fix

Collect all issuer data from the fetch results, deduplicate by CIK, then do a single multi-row INSERT before the form_d batch write:

```python
# Collect issuers
issuers = {}
for row, form_d in fetch_results:
    if form_d and form_d.issuer_name and form_d.cik not in issuers:
        issuers[form_d.cik] = {...}

# Batch upsert all issuers at once
await repo.upsert_companies_from_issuers_batch(list(issuers.values()))
```

## Files

- `air1/services/ingest/repo.py` — add `upsert_companies_from_issuers_batch()`
- `air1/services/ingest/service.py` — collect issuers and batch before form_d save
