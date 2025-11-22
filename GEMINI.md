# Air1 Project Context

## Project Overview
Air1 is a Python-based automation tool designed for lead generation and outreach, specifically targeting LinkedIn. It features a dual-interface architecture with a Command Line Interface (CLI) for executing workflows and a FastAPI backend for monitoring and potential future API expansions.

## Key Technologies
*   **Language:** Python 3.13+
*   **Package Management:** `uv`
*   **CLI Framework:** Typer
*   **Web Framework:** FastAPI
*   **Database:** PostgreSQL with Prisma ORM (`prisma-client-py`)
*   **Automation:** Playwright (Browser Automation)
*   **Email Service:** Resend
*   **Testing:** Pytest (Asyncio supported)

## Architecture
The project is organized into the following core modules within the `air1/` directory:

*   **`cli/`**: Contains the Typer-based CLI entry points and command definitions (`commands.py`).
*   **`db/`**: Handles database connections via Prisma and SQL loading utilities (`sql_loader.py`).
*   **`services/`**: Core business logic and external integrations.
    *   `outreach/`: Includes logic for browser automation (`browser.py`), email (`email.py`), and LinkedIn specific operations (`linkedin_outreach.py`).
*   **`workflows/`**: Orchestrates high-level tasks like extracting company leads (`linkedin_company_leads.py`).
*   **`app.py`**: A minimal FastAPI application currently providing health check endpoints.

## Development Workflow

### Prerequisites
*   Python 3.13+
*   `uv` package manager installed.
*   PostgreSQL database accessible.

### Setup & Dependencies
1.  **Install Dependencies:**
    ```bash
    uv sync
    ```
2.  **Database Setup:**
    ```bash
    # Generate Prisma Client
    uv run prisma generate
    # Push Schema to Database
    uv run prisma db push
    ```

### Running the Application
**CLI Commands:**
Execute commands using the project entry point:
```bash
# List available commands
uv run air1 --help

# Example: Scrape company leads
uv run air1 company_leads "Company Name" --limit 5

# Example: Send a test email
uv run air1 send_test_email user@example.com
```

**Web Server:**
Start the FastAPI development server:
```bash
uv run uvicorn air1.app:app --reload
```

### Testing
The project uses `pytest` with custom markers for different test levels.
```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit        # Fast, isolated tests
uv run pytest -m integration # Tests requiring DB/Network
uv run pytest -m slow        # Long-running tests
```

### Code Quality
Use the provided scripts to maintain code standards:
*   **Linting (Ruff):** `./lint.sh` (Auto-fixes issues)
*   **Compilation Check:** `./check.sh`

## File Structure Highlights
*   `air1/`: Source code root.
*   `prisma/schema.prisma`: Database schema definition.
*   `docker-compose.yml`: Container orchestration (likely for DB).
*   `pyproject.toml`: Dependency and tool configuration.
*   `CLAUDE.md`: Detailed developer guide and command reference.
