import pytest
from unittest.mock import AsyncMock, patch
from air1.services.outreach.browser import BrowserSession, LinkedInAuthenticator
from air1.services.outreach.linkedin_profile import CompanyPeople


@pytest.mark.asyncio
async def test_get_company_members_url_construction_no_keywords():
    """Test URL construction without keywords."""

    mock_browser = AsyncMock()
    authenticator = LinkedInAuthenticator(linkedin_sid="test_sid")
    session = BrowserSession(browser=mock_browser, authenticator=authenticator)

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
    authenticator = LinkedInAuthenticator(linkedin_sid="test_sid")
    session = BrowserSession(browser=mock_browser, authenticator=authenticator)

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
    authenticator = LinkedInAuthenticator(linkedin_sid="test_sid")
    session = BrowserSession(browser=mock_browser, authenticator=authenticator)

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
    authenticator = LinkedInAuthenticator(linkedin_sid="test_sid")
    session = BrowserSession(browser=mock_browser, authenticator=authenticator)

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
    authenticator = LinkedInAuthenticator(linkedin_sid="test_sid")
    session = BrowserSession(browser=mock_browser, authenticator=authenticator)

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


@pytest.mark.asyncio
async def test_linkedin_authenticator_applies_cookies():
    """Test that LinkedInAuthenticator correctly applies cookies to a page."""
    authenticator = LinkedInAuthenticator(linkedin_sid="test_sid_value")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.context = mock_context

    await authenticator.authenticate_page(mock_page)

    mock_context.add_cookies.assert_called_once()
    cookies = mock_context.add_cookies.call_args[0][0]
    assert len(cookies) == 1
    assert cookies[0]["name"] == "li_at"
    assert cookies[0]["value"] == "test_sid_value"
    assert cookies[0]["domain"] == ".linkedin.com"
    assert cookies[0]["path"] == "/"
    assert cookies[0]["secure"] is True
    assert cookies[0]["httpOnly"] is True
    assert cookies[0]["sameSite"] == "Lax"


@pytest.mark.asyncio
async def test_linkedin_authenticator_custom_domain():
    """Test LinkedInAuthenticator with custom domain for testing."""
    authenticator = LinkedInAuthenticator(linkedin_sid="test_sid", domain=".test.linkedin.com")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.context = mock_context

    await authenticator.authenticate_page(mock_page)

    cookies = mock_context.add_cookies.call_args[0][0]
    assert cookies[0]["domain"] == ".test.linkedin.com"


@pytest.mark.asyncio
async def test_linkedin_authenticator_empty_sid_skips_cookies():
    """Test that LinkedInAuthenticator with empty SID does not add cookies."""
    authenticator = LinkedInAuthenticator(linkedin_sid="")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.context = mock_context

    await authenticator.authenticate_page(mock_page)

    mock_context.add_cookies.assert_not_called()


@pytest.mark.asyncio
async def test_browser_session_uses_authenticator():
    """Test that BrowserSession delegates authentication to the authenticator."""
    mock_browser = AsyncMock()
    mock_authenticator = AsyncMock(spec=LinkedInAuthenticator)

    session = BrowserSession(browser=mock_browser, authenticator=mock_authenticator)

    mock_page = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    await session._setup_page()

    mock_authenticator.authenticate_page.assert_called_once_with(mock_page)


@pytest.mark.asyncio
async def test_linkedin_authenticator_none_sid_skips_cookies():
    """Test that LinkedInAuthenticator with None SID does not add cookies."""
    authenticator = LinkedInAuthenticator(linkedin_sid=None)

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.context = mock_context

    await authenticator.authenticate_page(mock_page)

    mock_context.add_cookies.assert_not_called()


@pytest.mark.asyncio
async def test_linkedin_authenticator_whitespace_sid_skips_cookies():
    """Test that LinkedInAuthenticator with whitespace-only SID does not add cookies."""
    authenticator = LinkedInAuthenticator(linkedin_sid="   ")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.context = mock_context

    await authenticator.authenticate_page(mock_page)

    mock_context.add_cookies.assert_not_called()
