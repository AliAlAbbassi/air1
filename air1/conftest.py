"""Pytest configuration and shared fixtures."""
import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--use-real-db",
        action="store_true",
        default=False,
        help="Run tests against real database instead of mocks",
    )


@pytest.fixture
def use_real_db(request):
    """Fixture to check if tests should use real database."""
    return request.config.getoption("--use-real-db", default=False)


@pytest.fixture
async def db_connection(use_real_db):
    """Fixture that connects to real DB or provides mock based on flag."""
    if use_real_db:
        from air1.db.prisma_client import connect_db, disconnect_db
        await connect_db()
        yield True
        await disconnect_db()
    else:
        yield False
