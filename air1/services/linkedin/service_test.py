import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from air1.services.linkedin.service import Service
from air1.services.linkedin.linkedin_profile import LinkedinProfile, CompanyPeople, Lead


@pytest.fixture
def mock_linkedin_profile():
    return LinkedinProfile(
        first_name="John",
        full_name="John Doe",
        email="john.doe@example.com",
        phone_number="123-456-7890",
        location="San Francisco",
        headline="Software Engineer",
    )


@pytest.fixture
def mock_company_people():
    return CompanyPeople(profile_ids={"profile1", "profile2"})


@pytest.mark.anyio
async def test_scrape_and_save_company_leads_success(
    mock_linkedin_profile, mock_company_people
):
    """Test successful scraping and saving of company leads"""

    with (
        patch("air1.services.linkedin.service.db") as mock_db,
        patch("air1.services.linkedin.service.async_playwright") as mock_playwright,
        patch.object(Service, "launch_browser") as mock_launch_browser,
        patch.object(Service, "save_linkedin_lead") as mock_save_lead,
    ):
        # Mock async playwright completely
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright_instance.__aexit__ = AsyncMock()

        # Setup mocks
        mock_db.connect = AsyncMock()

        mock_session = MagicMock()
        mock_session.get_company_members = AsyncMock(return_value=mock_company_people)
        mock_session.get_profile_info = AsyncMock(return_value=mock_linkedin_profile)
        mock_session.browser.close = AsyncMock()

        mock_launch_browser.return_value = mock_session
        mock_save_lead.return_value = 123  # mock lead_id

        # Create service and run test
        with patch.dict("os.environ", {"linkedin_sid": "test_sid"}):
            async with Service() as service:
                result = await service.scrape_and_save_company_leads(
                    "test-company", limit=2, headless=True
                )

            # Assertions
            assert result == 2  # Should save 2 leads
            mock_db.connect.assert_called_once()
            mock_launch_browser.assert_called_once_with(headless=True)
            mock_session.get_company_members.assert_called_once_with(
                "test-company", limit=2
            )
            assert mock_session.get_profile_info.call_count == 2
            assert mock_save_lead.call_count == 2
            mock_session.browser.close.assert_called_once()


@pytest.mark.anyio
async def test_scrape_and_save_company_leads_no_email():
    """Test scraping when profiles have no email"""

    profile_no_email = LinkedinProfile(
        first_name="Jane",
        full_name="Jane Smith",
        email="",  # No email
        phone_number="",
        location="New York",
        headline="Manager",
    )

    company_people = CompanyPeople(profile_ids={"profile1"})

    with (
        patch("air1.services.linkedin.service.db") as mock_db,
        patch("air1.services.linkedin.service.async_playwright") as mock_playwright,
        patch.object(Service, "launch_browser") as mock_launch_browser,
        patch.object(Service, "save_linkedin_lead") as mock_save_lead,
    ):
        # Mock async playwright completely
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright_instance.__aexit__ = AsyncMock()

        mock_db.connect = AsyncMock()

        mock_session = MagicMock()
        mock_session.get_company_members = AsyncMock(return_value=company_people)
        mock_session.get_profile_info = AsyncMock(return_value=profile_no_email)
        mock_session.browser.close = AsyncMock()

        mock_launch_browser.return_value = mock_session

        with patch.dict("os.environ", {"linkedin_sid": "test_sid"}):
            async with Service() as service:
                result = await service.scrape_and_save_company_leads(
                    "test-company", limit=1
                )

            # Should not save any leads due to missing email
            assert result == 0
            mock_save_lead.assert_not_called()


@pytest.mark.anyio
async def test_scrape_and_save_company_leads_save_error(
    mock_linkedin_profile, mock_company_people
):
    """Test handling of save errors"""

    with (
        patch("air1.services.linkedin.service.db") as mock_db,
        patch("air1.services.linkedin.service.async_playwright") as mock_playwright,
        patch.object(Service, "launch_browser") as mock_launch_browser,
        patch.object(Service, "save_linkedin_lead") as mock_save_lead,
    ):
        # Mock async playwright completely
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright_instance.__aexit__ = AsyncMock()

        mock_db.connect = AsyncMock()

        mock_session = MagicMock()
        mock_session.get_company_members = AsyncMock(return_value=mock_company_people)
        mock_session.get_profile_info = AsyncMock(return_value=mock_linkedin_profile)
        mock_session.browser.close = AsyncMock()

        mock_launch_browser.return_value = mock_session
        mock_save_lead.side_effect = Exception("Database error")

        with patch.dict("os.environ", {"linkedin_sid": "test_sid"}):
            async with Service() as service:
                result = await service.scrape_and_save_company_leads(
                    "test-company", limit=2
                )

            # Should handle errors gracefully and return 0 leads saved
            assert result == 0
            assert mock_save_lead.call_count == 2  # Still attempts to save
            mock_session.browser.close.assert_called_once()


@pytest.mark.anyio
async def test_scrape_and_save_company_leads_browser_cleanup():
    """Test that browser is always closed even on errors"""

    with (
        patch("air1.services.linkedin.service.db") as mock_db,
        patch("air1.services.linkedin.service.async_playwright") as mock_playwright,
        patch.object(Service, "launch_browser") as mock_launch_browser,
    ):
        # Mock async playwright completely
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright_instance.__aexit__ = AsyncMock()

        mock_db.connect = AsyncMock()

        mock_session = MagicMock()
        mock_session.get_company_members.side_effect = Exception("Scraping error")
        mock_session.browser.close = AsyncMock()

        mock_launch_browser.return_value = mock_session

        with patch.dict("os.environ", {"linkedin_sid": "test_sid"}):
            with pytest.raises(Exception):
                async with Service() as service:
                    await service.scrape_and_save_company_leads("test-company")

            # Browser should still be closed
            mock_session.browser.close.assert_called_once()


@pytest.mark.anyio
async def test_save_linkedin_lead_with_company_mapping(mock_linkedin_profile):
    """Test saving LinkedIn lead with company mapping"""

    mock_lead = Lead(
        first_name="John",
        full_name="John Doe",
        email="john.doe@example.com",
        phone_number="123-456-7890",
    )

    with (
        patch("air1.services.linkedin.service.async_playwright") as mock_playwright,
        patch("air1.services.linkedin.service.insert_lead") as mock_insert_lead,
        patch(
            "air1.services.linkedin.service.insert_linkedin_profile"
        ) as mock_insert_profile,
        patch(
            "air1.services.linkedin.service.insert_linkedin_company_member"
        ) as mock_insert_company,
    ):
        # Mock async playwright
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright_instance.__aexit__ = AsyncMock()

        # Mock database operations
        mock_insert_lead.return_value = (True, 123)  # success, lead_id
        mock_insert_profile.return_value = 456  # linkedin_profile_id
        mock_insert_company.return_value = AsyncMock()

        with patch.dict("os.environ", {"linkedin_sid": "test_sid"}):
            async with Service() as service:
                lead_id = await service.save_linkedin_lead(
                    mock_lead,
                    mock_linkedin_profile,
                    company_url="https://www.linkedin.com/company/test-company/",
                    company_name="Test Company",
                )

                # Assertions
                assert lead_id == 123
                mock_insert_lead.assert_called_once()
                mock_insert_profile.assert_called_once()
                mock_insert_company.assert_called_once_with(
                    456,
                    "https://www.linkedin.com/company/test-company/",
                    "Test Company",
                )


@pytest.mark.anyio
async def test_save_linkedin_lead_without_company():
    """Test saving LinkedIn lead without company mapping"""

    mock_lead = Lead(
        first_name="Jane",
        full_name="Jane Smith",
        email="jane.smith@example.com",
        phone_number="",
    )

    mock_profile = LinkedinProfile(
        first_name="Jane",
        full_name="Jane Smith",
        email="jane.smith@example.com",
        location="New York",
        headline="Manager",
    )

    with (
        patch("air1.services.linkedin.service.async_playwright") as mock_playwright,
        patch("air1.services.linkedin.service.insert_lead") as mock_insert_lead,
        patch(
            "air1.services.linkedin.service.insert_linkedin_profile"
        ) as mock_insert_profile,
        patch(
            "air1.services.linkedin.service.insert_linkedin_company_member"
        ) as mock_insert_company,
    ):
        # Mock async playwright
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright_instance.__aexit__ = AsyncMock()

        # Mock database operations
        mock_insert_lead.return_value = (True, 789)
        mock_insert_profile.return_value = 101112

        with patch.dict("os.environ", {"linkedin_sid": "test_sid"}):
            async with Service() as service:
                lead_id = await service.save_linkedin_lead(mock_lead, mock_profile)

                # Assertions
                assert lead_id == 789
                mock_insert_lead.assert_called_once()
                mock_insert_profile.assert_called_once()
                mock_insert_company.assert_not_called()  # Should not be called without company info
