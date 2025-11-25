# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Package Management & Dependencies:**
- `uv add <package>` - Add new dependencies
- `uv sync` - Install dependencies from lock file
- `uv run <command>` - Run commands in virtual environment

**Testing:**
- `uv run pytest` - Run all tests
- `uv run pytest -m unit` - Run only unit tests (fast, no external dependencies)
- `uv run pytest -m integration` - Run integration tests (requires database)
- `uv run pytest -m slow` - Run slow tests
- `uv run pytest -v --tb=short` - Run with verbose output and short tracebacks
- `uv run pytest --cov=air1` - Run tests with coverage

**Linting & Code Quality:**
- `./lint.sh` - Run linting with automatic fixes using Ruff
- `./check.sh` - Check Python compilation
- `uv run ruff check --fix air1/` - Direct Ruff linting with fixes
- `uv run python -m compileall air1/` - Check Python compilation

**Application Execution:**
- `uv run air1` or `uv run python -m air1` - Run CLI application
- `uv run uvicorn air1.app:app --reload` - Start FastAPI development server

**Database (Prisma):**
- `uv run prisma db pull` - Introspect database and update schema from existing DB
- `uv run prisma generate` - Generate Prisma client
- `uv run prisma db push` - Push schema changes to database

## Architecture Overview

**Core Structure:**
- `air1/` - Main package containing all application code
- `air1/__main__.py` - Entry point that delegates to CLI commands
- `air1/app.py` - FastAPI application with basic health endpoints
- `air1/config.py` - Configuration management using Pydantic Settings

**Key Components:**

**CLI Interface (`air1/cli/`):**
- Built with Typer framework
- `commands.py` - Main CLI command definitions and application entry point

**Database Layer (`air1/db/`):**
- Uses Prisma ORM for PostgreSQL
- `prisma_client.py` - Prisma client setup and connection management
- `sql_loader.py` - SQL query loading with aiosql and custom PrismaAdapter
- `query/` directory contains raw SQL queries:
  - `leads.sql` - Lead management queries
  - `linkedin.sql` - LinkedIn profile queries
  - `linkedin_company_members.sql` - Company member queries
  - `contact_point.sql` - Contact point management
- Schema includes: Lead, LinkedinProfile, LinkedinCompanyMember, ContactPoint models

**Business Logic (`air1/workflows/`):**
- `linkedin_outreach.py` - LinkedIn outreach automation workflows
- `linkedin_company_leads.py` - Company lead generation workflows
- `linkedin_profile_info.py` - Profile information extraction workflows

**Services Layer (`air1/services/outreach/`):**
- `service.py` - Main outreach service orchestration (implements IService interface)
- `linkedin_outreach.py` - LinkedIn-specific outreach operations
- `browser.py` - Browser automation using Playwright
- `profile_scraper.py` - LinkedIn profile scraping logic
- `company_scraper.py` - Company information scraping
- `email.py` - Email sending functionality using Resend
- `repo.py` - Database repository layer with aiosql integration
- `templates.py` - Email and message template management
- `contact_point.py` - Contact point management module

**Technology Stack:**
- **Web Framework:** FastAPI for HTTP API endpoints
- **CLI Framework:** Typer for command-line interface
- **Database:** PostgreSQL with Prisma ORM (prisma-client-py) + aiosql for raw SQL queries
- **Web Automation:** Playwright for browser automation
- **Email:** Resend service for email delivery
- **Configuration:** Pydantic Settings with dotenv support
- **Testing:** Pytest with asyncio support, separate test markers for unit/integration/slow tests
- **Code Quality:** Ruff for linting and formatting
- **Package Management:** UV for Python dependency management

**Test Organization:**
- Uses pytest with custom markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Test files follow pattern: `*_test.py` or `test_*.py`
- Asyncio mode enabled for async test support
- Coverage reporting available via pytest-cov

**Key Dependencies:**
- aiosql - SQL query management from .sql files
- beautifulsoup4, lxml - HTML parsing
- playwright - Browser automation
- prisma - Database ORM
- resend - Email service
- loguru - Structured logging
- rich - Terminal output formatting