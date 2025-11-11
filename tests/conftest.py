import pytest
import pytest_asyncio
import asyncpg
import asyncio
from typing import AsyncGenerator, Generator
from testcontainers.postgres import PostgresContainer
from air1.db.db import Database
from air1.config import settings
import os


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for integration tests."""
    postgres = PostgresContainer(
        image="postgres:16-alpine",
        username="testuser",
        password="testpass",
        dbname="testdb",
        driver="asyncpg"
    )
    postgres.start()

    yield postgres

    postgres.stop()


@pytest_asyncio.fixture(scope="function")
async def test_db_pool(postgres_container) -> AsyncGenerator[asyncpg.Pool, None]:
    """Create a test database pool for each test."""
    pool = await asyncpg.create_pool(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        database=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,
        min_size=1,
        max_size=5
    )

    # Create tables
    async with pool.acquire() as conn:
        # Drop existing tables first
        await conn.execute("DROP TABLE IF EXISTS linkedin_company_members CASCADE")
        await conn.execute("DROP TABLE IF EXISTS linkedin_profile CASCADE")
        await conn.execute("DROP TABLE IF EXISTS lead CASCADE")
        await conn.execute("DROP FUNCTION IF EXISTS update_updated_on_column CASCADE")

        # Read and execute schema files
        schema_dir = os.path.join(os.path.dirname(__file__), '..', 'air1', 'db', 'models')

        # Execute functions first
        functions_path = os.path.join(os.path.dirname(__file__), '..', 'air1', 'db', 'functions', 'functions.sql')
        if os.path.exists(functions_path):
            with open(functions_path, 'r') as f:
                await conn.execute(f.read())

        # Then create tables - execute the entire file at once to preserve PL/pgSQL functions
        for schema_file in ['lead.sql', 'linkedin.sql']:
            schema_path = os.path.join(schema_dir, schema_file)
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    sql = f.read()
                    # Execute the entire SQL file at once
                    await conn.execute(sql)

    yield pool

    await pool.close()


@pytest_asyncio.fixture
async def test_db(test_db_pool) -> Database:
    """Create a test database instance."""
    db = Database()
    db.pool = test_db_pool
    return db


@pytest_asyncio.fixture
async def clean_db(test_db_pool):
    """Clean all data from tables before each test."""
    async with test_db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE linkedin_company_members, linkedin_profile, lead RESTART IDENTITY CASCADE")


@pytest.fixture
def mock_settings(monkeypatch, postgres_container):
    """Mock settings for tests."""
    monkeypatch.setattr(settings, 'database_host', postgres_container.get_container_host_ip())
    monkeypatch.setattr(settings, 'database_port', postgres_container.get_exposed_port(5432))
    monkeypatch.setattr(settings, 'database_name', postgres_container.dbname)
    monkeypatch.setattr(settings, 'database_user', postgres_container.username)
    monkeypatch.setattr(settings, 'database_password', postgres_container.password)
    return settings