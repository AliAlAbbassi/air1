import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from air1.services.linkedin.service import Service
from air1.services.linkedin.linkedin_profile import LinkedinProfile, CompanyPeople, Lead
from air1.db.db import init_pool, close_pool


@pytest_asyncio.fixture
async def setup_db():
    """Initialize database pool for tests."""
    await init_pool()
    yield
    await close_pool()


@pytest.mark.asyncio
async def test_scrape_company_leads_with_mock(setup_db):
    """Test scraping company leads with mocked browser."""

    mock_playwright = MagicMock()
    mock_browser = AsyncMock()

    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_company_people = CompanyPeople(profile_ids={"john-doe", "jane-smith"})

    mock_profiles = {
        "john-doe": LinkedinProfile(
            profile_id="john-doe",
            first_name="John",
            full_name="John Doe",
            headline="Software Engineer",
            location="San Francisco, CA",
            linkedin_url="https://linkedin.com/in/john-doe",
            email="john.doe@example.com",
            phone_number="+1234567890"
        ),
        "jane-smith": LinkedinProfile(
            profile_id="jane-smith",
            first_name="Jane",
            full_name="Jane Smith",
            headline="Product Manager",
            location="New York, NY",
            linkedin_url="https://linkedin.com/in/jane-smith",
            email="jane.smith@example.com",
            phone_number="+9876543210"
        )
    }

    with patch('air1.services.linkedin.service.BrowserSession') as MockBrowserSession:
        mock_session_instance = AsyncMock()
        MockBrowserSession.return_value = mock_session_instance

        mock_session_instance.get_company_members = AsyncMock(return_value=mock_company_people)
        mock_session_instance.get_profile_info = AsyncMock(
            side_effect=lambda profile_id: mock_profiles.get(profile_id, LinkedinProfile())
        )
        mock_session_instance.browser.close = AsyncMock()

        service = Service(playwright=mock_playwright)

        results = await service.scrape_company_leads(
            company_ids=["test-company"],
            limit=10,
            headless=True
        )

        assert "test-company" in results
        assert results["test-company"] == 2

        mock_session_instance.get_company_members.assert_called_once_with("test-company", limit=10)
        assert mock_session_instance.get_profile_info.call_count == 2


@pytest.mark.asyncio
async def test_scrape_multiple_companies(setup_db):
    """Test scraping multiple companies."""

    mock_playwright = MagicMock()
    mock_browser = AsyncMock()

    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch('air1.services.linkedin.service.BrowserSession') as MockBrowserSession:
        mock_session_instance = AsyncMock()
        MockBrowserSession.return_value = mock_session_instance

        mock_session_instance.get_company_members = AsyncMock(
            return_value=CompanyPeople(profile_ids=set())
        )
        mock_session_instance.browser.close = AsyncMock()

        service = Service(playwright=mock_playwright)

        results = await service.scrape_company_leads(
            company_ids=["company1", "company2", "company3"],
            limit=5,
            headless=True
        )

        assert len(results) == 3
        assert "company1" in results
        assert "company2" in results
        assert "company3" in results


@pytest.mark.asyncio
async def test_service_context_manager():
    """Test Service async context manager."""

    mock_playwright = MagicMock()
    async with Service(playwright=mock_playwright) as service:
        assert service.playwright == mock_playwright
        assert service._owns_playwright is False

    with patch('air1.services.linkedin.service.async_playwright') as mock_async_playwright:
        mock_playwright_instance = AsyncMock()
        mock_async_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright_instance.__aexit__ = AsyncMock()

        async with Service() as service:
            assert service._owns_playwright is True
            assert service.playwright is not None

        mock_playwright_instance.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_scrape_with_no_emails(setup_db):
    """Test handling profiles without emails."""

    mock_playwright = MagicMock()
    mock_browser = AsyncMock()

    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    profiles_without_email = {
        "no-email-1": LinkedinProfile(
            profile_id="no-email-1",
            first_name="Bob",
            full_name="Bob Smith",
            headline="Engineer",
            location="Chicago, IL",
            email=""
        ),
        "no-email-2": LinkedinProfile(
            profile_id="no-email-2",
            first_name="Alice",
            full_name="Alice Johnson",
            headline="Designer",
            location="Austin, TX",
            email=""
        )
    }

    with patch('air1.services.linkedin.service.BrowserSession') as MockBrowserSession:
        mock_session_instance = AsyncMock()
        MockBrowserSession.return_value = mock_session_instance

        mock_session_instance.get_company_members = AsyncMock(
            return_value=CompanyPeople(profile_ids={"no-email-1", "no-email-2"})
        )
        mock_session_instance.get_profile_info = AsyncMock(
            side_effect=lambda pid: profiles_without_email.get(pid, LinkedinProfile())
        )
        mock_session_instance.browser.close = AsyncMock()

        service = Service(playwright=mock_playwright)

        results = await service.scrape_company_leads(
            company_ids=["test-company"],
            limit=10,
            headless=True
        )

        assert results["test-company"] == 0


@pytest.mark.asyncio
async def test_scrape_and_save_error_handling(setup_db):
    """Test error handling during save operation."""

    mock_playwright = MagicMock()
    mock_browser = AsyncMock()

    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_profile = LinkedinProfile(
        profile_id="error-test",
        first_name="Error",
        full_name="Error Test",
        email="error@test.com",
        headline="Test"
    )

    with patch('air1.services.linkedin.service.BrowserSession') as MockBrowserSession:
        with patch('air1.services.linkedin.service.save_lead_complete') as mock_save:
            mock_session_instance = AsyncMock()
            MockBrowserSession.return_value = mock_session_instance

            mock_session_instance.get_company_members = AsyncMock(
                return_value=CompanyPeople(profile_ids={"error-test"})
            )
            mock_session_instance.get_profile_info = AsyncMock(return_value=mock_profile)
            mock_session_instance.browser.close = AsyncMock()

            # Simulate save failure
            mock_save.side_effect = Exception("Database error")

            service = Service(playwright=mock_playwright)

            results = await service.scrape_company_leads(
                company_ids=["test-company"],
                limit=10,
                headless=True
            )

            # Should return 0 saved due to error
            assert results["test-company"] == 0
            mock_save.assert_called_once()
