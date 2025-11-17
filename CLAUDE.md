# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Air1 is a LinkedIn lead generation and outreach automation tool built with Python. It scrapes company employee information from LinkedIn and automates connection outreach workflows using browser automation.

## Technology Stack

- **Python 3.13+** with UV package manager
- **FastAPI** for web API endpoints
- **Typer** for CLI interface
- **PostgreSQL** with AsyncPG driver
- **Playwright** for browser automation
- **Pytest** for testing
- **Alembic** for database migrations
- **Ruff** for linting and formatting

## Essential Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Start local PostgreSQL
docker-compose up -d

# Run database migrations
uv run alembic upgrade head
```

### Code Quality
```bash
# Lint and auto-fix code
./lint.sh

# Check for syntax errors
./check.sh

# Run all tests
uv run pytest

# Run specific test types
uv run pytest -m unit
uv run pytest -m integration
```

### Running the Application
```bash
# CLI interface
uv run air1 --help
uv run air1 company-leads tech-usa --limit 10

# Web API server
uv run python start.py
# Alternative: uvicorn air1.app:app --reload

# Direct Python execution
uv run python main.py
```

## Architecture

### Core Components

**Browser Automation Service** (`air1/services/browser/`):
- `browser.py`: Playwright session management with LinkedIn authentication
- `linkedin_outreach.py`: Automates connection requests
- `company_scraper.py`: Extracts employee lists from company pages
- `profile_scraper.py`: Scrapes individual profile data

**Database Layer** (`air1/db/`):
- `models/`: PostgreSQL schema definitions
- `query/`: SQL templates using aiosql
- `db.py`: AsyncPG connection pool management

**Configuration** (`air1/config.py`):
- Environment-based settings with Pydantic
- LinkedIn session management via `LINKEDIN_SID` environment variable

### Key Patterns

- **Async-first architecture**: All I/O operations use asyncio
- **Service pattern**: Clean separation between browser automation and business logic
- **Configuration-driven**: Extensive use of environment variables
- **Type safety**: Pydantic models for data validation

### Database Schema

Main entities:
- `leads`: Core lead information
- `linkedin_profile`: LinkedIn profile data
- `linkedin_company_members`: Company-employee relationships

### Testing Structure

- Tests embedded within modules as `*_test.py` files
- Unit tests (fast, no database required)
- Integration tests (require PostgreSQL)
- Async test support configured in `pytest.ini`

## Environment Requirements

Required environment variables:
- `LINKEDIN_SID`: LinkedIn session ID for authentication
- Database credentials (defaults work for local development with docker-compose)

## Development Workflow

1. **Setup**: `docker-compose up -d && uv sync`
2. **Database**: `uv run alembic upgrade head`
3. **Code Quality**: Use `./lint.sh` before commits
4. **Testing**: `uv run pytest` for validation
5. **Usage**: `uv run air1 company-leads [companies]` for lead generation

## Entry Points

- **CLI**: `air1/__main__.py` - Main CLI interface
- **Web API**: `air1/app.py` - FastAPI application
- **Direct execution**: `main.py` - Direct Python entry point