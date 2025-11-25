import pytest
from unittest.mock import AsyncMock, patch
from air1.services.outreach.browser import BrowserSession
from air1.services.outreach.linkedin_profile import CompanyPeople


@pytest.mark.asyncio
async def test_get_company_members_url_construction_no_keywords():
    """Test URL construction without keywords."""

    mock_browser = AsyncMock()
    session = BrowserSession(browser=mock_browser, linkedin_sid="test_sid")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()

    with (
        patch.object(session, '_setup_page', return_value=mock_page),
        patch('air1.services.outreach.browser.navigate_to_linkedin_url') as mock_nav,
        patch('air1.services.outreach.company_scraper.CompanyScraper.extract_company_members',
              AsyncMock(return_value=CompanyPeople(profile_ids=set())))
    ):

        await session.get_company_members("testcompany", limit=5)

        # Verify URL called without keywords parameter
        mock_nav.assert_called_once_with(
            mock_page,
            "https://www.linkedin.com/company/testcompany/people/"
        )


@pytest.mark.asyncio
async def test_get_company_members_url_construction_single_keyword():
    """Test URL construction with single keyword."""

    mock_browser = AsyncMock()
    session = BrowserSession(browser=mock_browser, linkedin_sid="test_sid")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()

    with (
        patch.object(session, '_setup_page', return_value=mock_page),
        patch('air1.services.outreach.browser.navigate_to_linkedin_url') as mock_nav,
        patch('air1.services.outreach.company_scraper.CompanyScraper.extract_company_members',
              AsyncMock(return_value=CompanyPeople(profile_ids=set())))
    ):

        await session.get_company_members("testcompany", limit=5, keywords=["talent"])

        # Verify URL called with single keyword
        mock_nav.assert_called_once_with(
            mock_page,
            "https://www.linkedin.com/company/testcompany/people/?keywords=talent"
        )


@pytest.mark.asyncio
async def test_get_company_members_url_construction_multiple_keywords():
    """Test URL construction with multiple keywords."""

    mock_browser = AsyncMock()
    session = BrowserSession(browser=mock_browser, linkedin_sid="test_sid")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()

    with (
        patch.object(session, '_setup_page', return_value=mock_page),
        patch('air1.services.outreach.browser.navigate_to_linkedin_url') as mock_nav,
        patch('air1.services.outreach.company_scraper.CompanyScraper.extract_company_members',
              AsyncMock(return_value=CompanyPeople(profile_ids=set())))
    ):

        await session.get_company_members(
            "testcompany",
            limit=5,
            keywords=["talent", "recruitment", "hr"]
        )

        # Verify URL called with comma-separated keywords
        mock_nav.assert_called_once_with(
            mock_page,
            "https://www.linkedin.com/company/testcompany/people/?keywords=talent,recruitment,hr"
        )


@pytest.mark.asyncio
async def test_get_company_members_url_construction_empty_keywords_list():
    """Test URL construction with empty keywords list."""

    mock_browser = AsyncMock()
    session = BrowserSession(browser=mock_browser, linkedin_sid="test_sid")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()

    with (
        patch.object(session, '_setup_page', return_value=mock_page),
        patch('air1.services.outreach.browser.navigate_to_linkedin_url') as mock_nav,
        patch('air1.services.outreach.company_scraper.CompanyScraper.extract_company_members',
              AsyncMock(return_value=CompanyPeople(profile_ids=set())))
    ):

        await session.get_company_members("testcompany", limit=5, keywords=[])

        # Verify URL called without keywords parameter when list is empty
        mock_nav.assert_called_once_with(
            mock_page,
            "https://www.linkedin.com/company/testcompany/people/"
        )


@pytest.mark.asyncio
async def test_get_company_members_keywords_with_special_chars():
    """Test URL construction with keywords containing special characters."""

    mock_browser = AsyncMock()
    session = BrowserSession(browser=mock_browser, linkedin_sid="test_sid")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()

    with (
        patch.object(session, '_setup_page', return_value=mock_page),
        patch('air1.services.outreach.browser.navigate_to_linkedin_url') as mock_nav,
        patch('air1.services.outreach.company_scraper.CompanyScraper.extract_company_members',
              AsyncMock(return_value=CompanyPeople(profile_ids=set())))
    ):

        # Test with keywords that have spaces and special characters
        await session.get_company_members(
            "testcompany",
            limit=5,
            keywords=["software engineer", "C++", "full-stack"]
        )

        # LinkedIn should handle these as-is in the URL
        mock_nav.assert_called_once_with(
            mock_page,
            "https://www.linkedin.com/company/testcompany/people/?keywords=software engineer,C++,full-stack"
        )