# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Environment
- Use `uv` for dependency management (replaces pip/poetry)
- Run commands with `uv run <command>`

### Testing
- Tests are embedded in the main code with `*_test.py` naming convention
- Run tests: `uv run pytest`
- Test markers available:
  - `@pytest.mark.unit` - Fast tests with no external dependencies
  - `@pytest.mark.integration` - Tests requiring database
  - `@pytest.mark.slow` - Long-running tests
- Run specific test types: `uv run pytest -m unit` or `uv run pytest -m integration`

### Linting and Code Quality
- Lint code: `./lint.sh` (uses ruff with auto-fix)
- Check compilation: `./check.sh`
- Check specific file: `./check.sh path/to/file.py`

### Database
- Database migrations with Alembic: `alembic upgrade head`
- Create migration: `alembic revision --autogenerate -m "description"`
- Docker Compose for database: `docker-compose up -d`

### CLI Usage
- Main CLI entry: `uv run air1 <command>`
- Available commands:
  - `air1 hello <name>` - Test command
  - `air1 company-leads <companies...> --limit <n>` - Scrape LinkedIn company leads

## Architecture Overview

### Core Structure
- **air1/cli/commands.py** - Main CLI commands using Typer
- **air1/config.py** - Application settings using Pydantic Settings (supports .env)
- **air1/services/browser/** - LinkedIn scraping service using Playwright
- **air1/workflows/** - High-level business workflows
- **air1/db/** - Database layer with AsyncPG and Alembic migrations

### Key Services
- **BrowserService** - Manages Playwright sessions for web scraping
- **LinkedinProfile** - Data models and parsing for LinkedIn profiles
- **Repository layer** - Database operations for lead storage

### Database Design
- Uses PostgreSQL with AsyncPG driver
- SQL queries stored in `air1/db/query/*.sql` files
- Models defined in `air1/db/models/`
- Supports connection pooling (configurable via settings)

### Configuration
All configuration via environment variables or .env file:
- Database connection settings (host, port, user, password)
- LinkedIn session ID (`LINKEDIN_SID`) - required for scraping
- Logging configuration (level, format, rotation)
- Connection pool settings

### LinkedIn Scraping Workflow
1. Service initializes Playwright browser with LinkedIn session cookie
2. Navigates to company pages and extracts employee profiles
3. Parses profile data into structured format
4. Saves leads to database via repository layer
5. Returns count of leads scraped per company

### Testing Strategy
- Tests co-located with source code (`*_test.py` files)
- Uses pytest-asyncio for async test support
- Testcontainers for integration tests with real PostgreSQL
- Faker for test data generation