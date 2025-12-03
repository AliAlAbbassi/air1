# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Package Management:** `uv add <package>`, `uv sync`, `uv run <command>`

**Testing:**
- `uv run pytest` - Run all tests
- `uv run pytest -m unit` - Unit tests only (fast, no external deps)
- `uv run pytest -m integration` - Integration tests (requires database)
- `uv run pytest path/to/test_file.py::test_name` - Run single test
- `uv run pytest --cov=air1` - With coverage

**Linting:** `./lint.sh` (runs Ruff with auto-fix and compilation check)

**Application:**
- `uv run air1` - Run CLI
- `uv run uvicorn air1.app:app --reload` - FastAPI dev server

**Database (Prisma):**
- `uv run prisma db pull` - Sync schema from existing DB
- `uv run prisma generate` - Generate client after schema changes

**Workflows:**
- `uv run python air1/workflows/linkedin_outreach_single_profile.py` - Connect with LinkedIn profiles (edit usernames in file first)
- `uv run python air1/workflows/linkedin_outreach.py` - LinkedIn outreach workflow
- `uv run python air1/workflows/linkedin_company_leads.py` - Company leads workflow
- `uv run python air1/workflows/linkedin_profile_info.py` - Profile info workflow

## Architecture Overview

**Entry Points:**
- `air1/__main__.py` → CLI commands via Typer
- `air1/app.py` → FastAPI endpoints

**Database Pattern:**
The codebase uses a hybrid Prisma + aiosql approach:
- Prisma handles connection management and transactions (`air1/db/prisma_client.py`)
- Raw SQL queries live in `air1/db/query/*.sql` files
- Custom `PrismaAdapter` in `sql_loader.py` bridges aiosql to Prisma's `query_raw`
- Query methods are typed via `OutreachQueries` Protocol

**Services Layer (`air1/services/outreach/`):**
- `service.py` - Main `Service` class (async context manager) orchestrates browser sessions
- `browser.py` - `BrowserSession` wraps Playwright for LinkedIn automation
- `repo.py` - Database repository functions using aiosql queries
- `email.py` - Resend email integration

**Workflows (`air1/workflows/`):**
Higher-level business logic composing services for multi-step operations.

## Testing Conventions

- Test files: `*_test.py` (colocated with source)
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Async tests auto-detected (asyncio_mode = auto)

## Environment Variables

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `RESEND_API_KEY` - For email functionality

**Conditional:**
- `LINKEDIN_SID` - Required for authenticated LinkedIn scraping (set `use_auth=True`)

**Optional (Proxy Configuration):**
- `PROXY_SERVER` - Proxy server URL (e.g., `http://proxy.example.com:8080`)
- `PROXY_USERNAME` - Proxy authentication username
- `PROXY_PASSWORD` - Proxy authentication password

See `.env.example` for detailed configuration instructions.

## LinkedIn Scraping Modes

The scraping service supports two modes:

**1. Authenticated Mode (default):**
- Requires `LINKEDIN_SID` environment variable
- Uses your LinkedIn account session

**2. Unauthenticated Mode:**
- No `LINKEDIN_SID` required
- Recommended with proxy rotation

**Usage:**
```python
# Authenticated with proxy
async with Service(use_auth=True) as service:
    await service.scrape_company_leads(companies, use_proxy=True)

# Unauthenticated with proxy
async with Service(use_auth=False) as service:
    await service.scrape_company_leads(companies, use_proxy=True)
```