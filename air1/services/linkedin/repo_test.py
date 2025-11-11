import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from air1.services.linkedin.repo import insert_lead, insert_linkedin_profile, insert_linkedin_company_member
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile


@pytest.fixture
def mock_lead():
    return Lead(
        first_name="John",
        full_name="John Doe",
        email="john.doe@example.com",
        phone_number="123-456-7890"
    )


@pytest.fixture
def mock_linkedin_profile():
    return LinkedinProfile(
        first_name="John",
        full_name="John Doe",
        email="john.doe@example.com",
        phone_number="123-456-7890",
        location="San Francisco",
        headline="Software Engineer",
        about="Experienced developer with 5 years in tech"
    )


@pytest.mark.anyio
async def test_insert_lead_success(mock_lead):
    """Test successful lead insertion"""

    with patch('air1.services.linkedin.repo.db') as mock_db, \
         patch('air1.services.linkedin.repo.queries') as mock_queries:

        mock_conn = MagicMock()
        mock_db.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db.pool.acquire.return_value.__aexit__ = AsyncMock()

        mock_queries.insert_lead = AsyncMock(return_value=123)

        success, lead_id = await insert_lead(mock_lead)

        assert success is True
        assert lead_id == 123
        mock_queries.insert_lead.assert_called_once_with(
            mock_conn, "John", "John Doe", "john.doe@example.com", "123-456-7890"
        )


@pytest.mark.anyio
async def test_insert_lead_failure(mock_lead):
    """Test lead insertion failure"""

    with patch('air1.services.linkedin.repo.db') as mock_db, \
         patch('air1.services.linkedin.repo.queries') as mock_queries:

        mock_conn = MagicMock()
        mock_db.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db.pool.acquire.return_value.__aexit__ = AsyncMock()

        mock_queries.insert_lead = AsyncMock(side_effect=Exception("Database error"))

        success, lead_id = await insert_lead(mock_lead)

        assert success is False
        assert lead_id is None


@pytest.mark.anyio
async def test_insert_linkedin_profile_success(mock_linkedin_profile):
    """Test successful LinkedIn profile insertion"""

    with patch('air1.services.linkedin.repo.db') as mock_db, \
         patch('air1.services.linkedin.repo.queries') as mock_queries:

        mock_conn = MagicMock()
        mock_db.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db.pool.acquire.return_value.__aexit__ = AsyncMock()

        mock_queries.insert_linkedin_profile = AsyncMock(return_value=456)

        profile_id = await insert_linkedin_profile(mock_linkedin_profile, 123)

        assert profile_id == 456
        mock_queries.insert_linkedin_profile.assert_called_once_with(
            mock_conn, 123, "", "San Francisco", "Software Engineer", "Experienced developer with 5 years in tech"
        )


@pytest.mark.anyio
async def test_insert_linkedin_company_member_success():
    """Test successful company member mapping insertion"""

    with patch('air1.services.linkedin.repo.db') as mock_db, \
         patch('air1.services.linkedin.repo.queries') as mock_queries:

        mock_conn = MagicMock()
        mock_db.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db.pool.acquire.return_value.__aexit__ = AsyncMock()

        mock_queries.insert_linkedin_company_member = AsyncMock()

        await insert_linkedin_company_member(
            linkedin_profile_id=456,
            company_url="https://www.linkedin.com/company/test-company/",
            company_name="Test Company"
        )

        mock_queries.insert_linkedin_company_member.assert_called_once_with(
            mock_conn, 456, "https://www.linkedin.com/company/test-company/", "Test Company"
        )


@pytest.mark.anyio
async def test_insert_linkedin_company_member_without_name():
    """Test company member mapping insertion without company name"""

    with patch('air1.services.linkedin.repo.db') as mock_db, \
         patch('air1.services.linkedin.repo.queries') as mock_queries:

        mock_conn = MagicMock()
        mock_db.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db.pool.acquire.return_value.__aexit__ = AsyncMock()

        mock_queries.insert_linkedin_company_member = AsyncMock()

        await insert_linkedin_company_member(
            linkedin_profile_id=456,
            company_url="https://www.linkedin.com/company/test-company/"
        )

        mock_queries.insert_linkedin_company_member.assert_called_once_with(
            mock_conn, 456, "https://www.linkedin.com/company/test-company/", None
        )


@pytest.mark.anyio
async def test_insert_linkedin_profile_failure(mock_linkedin_profile):
    """Test LinkedIn profile insertion failure"""

    with patch('air1.services.linkedin.repo.db') as mock_db, \
         patch('air1.services.linkedin.repo.queries') as mock_queries:

        mock_conn = MagicMock()
        mock_db.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db.pool.acquire.return_value.__aexit__ = AsyncMock()

        mock_queries.insert_linkedin_profile = AsyncMock(side_effect=Exception("Database error"))

        profile_id = await insert_linkedin_profile(mock_linkedin_profile, 123)

        assert profile_id is None