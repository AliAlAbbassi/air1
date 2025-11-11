"""
Integration tests using a mock database connection for environments without Docker.
To run real integration tests with PostgreSQL, install Docker and run:
    uv run pytest tests/integration/test_repo_integration.py -m integration
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from faker import Faker
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile
from air1.services.linkedin.repo import insert_lead, insert_linkedin_profile, insert_linkedin_company_member
from air1.db import db as db_module

fake = Faker()

pytestmark = pytest.mark.asyncio


class TestRepositoryIntegrationMock:
    """Integration tests with mocked database for environments without Docker."""

    @pytest_asyncio.fixture
    async def setup_mock_db(self):
        """Setup mock database pool."""
        # Create mock pool
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        # Setup acquire context manager properly
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager

        # Store original pool and replace with mock
        original_pool = db_module.pool
        db_module.pool = mock_pool

        yield mock_conn

        # Restore original pool
        db_module.pool = original_pool

    async def test_insert_lead_new(self, setup_mock_db):
        """Test inserting a new lead with mocked DB."""
        mock_conn = setup_mock_db

        # Mock the query result
        with patch('air1.services.linkedin.repo.queries.insert_lead', new_callable=AsyncMock) as mock_insert:
            # Mock a Record object with lead_id
            mock_record = MagicMock()
            mock_record.get.return_value = 1
            mock_record.__getitem__.return_value = 1
            mock_insert.return_value = mock_record

            lead = Lead(
                first_name=fake.first_name(),
                full_name=fake.name(),
                email=fake.email(),
                phone_number=fake.phone_number()
            )

            success, lead_id = await insert_lead(lead)

            assert success is True
            assert lead_id == 1
            mock_insert.assert_called_once()

    async def test_insert_lead_error_handling(self, setup_mock_db):
        """Test error handling when insert fails."""
        with patch('air1.services.linkedin.repo.queries.insert_lead', new_callable=AsyncMock) as mock_insert:
            mock_insert.side_effect = Exception("Database error")

            lead = Lead(email=fake.email())

            success, lead_id = await insert_lead(lead)

            assert success is False
            assert lead_id is None

    async def test_insert_linkedin_profile(self, setup_mock_db):
        """Test inserting a LinkedIn profile with mocked DB."""
        mock_conn = setup_mock_db

        with patch('air1.services.linkedin.repo.queries.insert_linkedin_profile', new_callable=AsyncMock) as mock_insert:
            # Mock a Record object with linkedin_profile_id
            mock_record = MagicMock()
            mock_record.get.return_value = 1
            mock_record.__getitem__.return_value = 1
            mock_insert.return_value = mock_record

            profile = LinkedinProfile(
                first_name=fake.first_name(),
                full_name=fake.name(),
                email=fake.email(),
                linkedin_url=f"https://linkedin.com/in/{fake.user_name()}",
                location=fake.city(),
                headline=fake.job()
            )

            profile_id = await insert_linkedin_profile(profile, 1)

            assert profile_id == 1
            mock_insert.assert_called_once()

    async def test_insert_linkedin_company_member(self, setup_mock_db):
        """Test inserting a company member with mocked DB."""
        mock_conn = setup_mock_db

        with patch('air1.services.linkedin.repo.queries.insert_linkedin_company_member', new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = None

            await insert_linkedin_company_member(
                1,
                f"https://linkedin.com/company/{fake.company()}",
                fake.company()
            )

            mock_insert.assert_called_once()


# Note: For real database integration tests with PostgreSQL in Docker,
# install Docker and run: uv run pytest tests/integration/test_repo_integration.py