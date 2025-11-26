from unittest.mock import AsyncMock, MagicMock

import pytest

from air1.services.outreach.linkedin_profile import ProfileExperience
from air1.services.outreach.navigation import navigate_to_linkedin_url
from air1.services.outreach.profile_scraper import ProfileScraper
from air1.services.outreach.service import Service


@pytest.mark.unit
class TestExtractProfileExperience:
    """Tests for ProfileScraper.extract_profile_experience"""

    @pytest.mark.asyncio
    async def test_extract_experience_no_section_found(self):
        """Test returns empty list when no experience section exists."""
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        # All selectors return no elements
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await ProfileScraper.extract_profile_experience(mock_page)

        assert result == []

    @pytest.mark.asyncio
    async def test_extract_experience_empty_section(self):
        """Test returns empty list when experience section has no items."""
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        # Experience section exists but has no list items
        mock_section = AsyncMock()
        mock_section.locator = MagicMock(return_value=AsyncMock())
        mock_section.locator.return_value.all = AsyncMock(return_value=[])

        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_section
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await ProfileScraper.extract_profile_experience(mock_page)

        assert result == []

    @pytest.mark.asyncio
    async def test_extract_experience_single_item(self):
        """Test extracts single experience item correctly."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        # Create mock experience item
        mock_item = AsyncMock()

        # Mock title extraction
        mock_title_elem = AsyncMock()
        mock_title_elem.count = AsyncMock(return_value=1)
        mock_title_elem.text_content = AsyncMock(return_value="Software Engineer")

        # Mock company link
        mock_company_link = AsyncMock()
        mock_company_link.count = AsyncMock(return_value=1)
        mock_company_link.get_attribute = AsyncMock(return_value="/company/acme-corp/")

        # Mock date element
        mock_date_elem = AsyncMock()
        mock_date_elem.count = AsyncMock(return_value=1)
        mock_date_elem.text_content = AsyncMock(return_value="Jan 2020 - Present")

        def item_locator_side_effect(selector):
            mock = AsyncMock()
            if "t-bold" in selector and "aria-hidden" in selector:
                mock.first = mock_title_elem
            elif "/company/" in selector:
                mock.first = mock_company_link
            elif "pvs-entity__caption-wrapper" in selector:
                mock.first = mock_date_elem
            else:
                mock.first = AsyncMock(count=AsyncMock(return_value=0))
            return mock

        mock_item.locator = MagicMock(side_effect=item_locator_side_effect)

        # Mock page.locator to return experience items
        mock_experience_locator = AsyncMock()
        mock_experience_locator.all = AsyncMock(return_value=[mock_item])
        mock_page.locator = MagicMock(return_value=mock_experience_locator)

        result = await ProfileScraper.extract_profile_experience(mock_page)

        assert len(result) == 1
        assert result[0].title == "Software Engineer"
        assert result[0].company_id == "acme-corp"
        assert result[0].start_date == "Jan 2020"


@pytest.mark.unit
class TestParseExperienceItem:
    """Tests for ProfileScraper._parse_experience_item"""

    @pytest.mark.asyncio
    async def test_parse_item_with_all_fields(self):
        """Test parsing item with title, company, and date."""
        mock_item = AsyncMock()

        # Mock title
        mock_title_elem = AsyncMock()
        mock_title_elem.count = AsyncMock(return_value=1)
        mock_title_elem.text_content = AsyncMock(return_value="Product Manager")

        # Mock company link
        mock_company_link = AsyncMock()
        mock_company_link.count = AsyncMock(return_value=1)
        mock_company_link.get_attribute = AsyncMock(
            return_value="https://www.linkedin.com/company/12345/"
        )

        # Mock date
        mock_date_elem = AsyncMock()
        mock_date_elem.count = AsyncMock(return_value=1)
        mock_date_elem.text_content = AsyncMock(return_value="Mar 2019 - Dec 2022")

        # Mock empty element for fallback selectors
        mock_empty = AsyncMock()
        mock_empty.count = AsyncMock(return_value=0)

        def locator_side_effect(selector):
            mock = AsyncMock()
            if "t-bold" in selector and "aria-hidden" in selector:
                mock.first = mock_title_elem
            elif "/company/" in selector:
                mock.first = mock_company_link
            elif "pvs-entity__caption-wrapper" in selector:
                mock.first = mock_date_elem
            else:
                mock.first = mock_empty
            return mock

        mock_item.locator = MagicMock(side_effect=locator_side_effect)

        result = await ProfileScraper._parse_experience_item(mock_item)

        assert result is not None
        assert result.title == "Product Manager"
        assert result.company_id == "12345"
        assert result.start_date == "Mar 2019"

    @pytest.mark.asyncio
    async def test_parse_item_title_only(self):
        """Test parsing item with only title."""
        mock_item = AsyncMock()

        mock_title_elem = AsyncMock()
        mock_title_elem.count = AsyncMock(return_value=1)
        mock_title_elem.text_content = AsyncMock(return_value="Consultant")

        mock_empty = AsyncMock()
        mock_empty.count = AsyncMock(return_value=0)

        def locator_side_effect(selector):
            mock = AsyncMock()
            if "t-bold" in selector and "aria-hidden" in selector:
                mock.first = mock_title_elem
            else:
                mock.first = mock_empty
            return mock

        mock_item.locator = MagicMock(side_effect=locator_side_effect)

        result = await ProfileScraper._parse_experience_item(mock_item)

        assert result is not None
        assert result.title == "Consultant"
        assert result.company_id is None
        assert result.start_date is None

    @pytest.mark.asyncio
    async def test_parse_item_company_only(self):
        """Test parsing item with only company ID."""
        mock_item = AsyncMock()

        mock_empty = AsyncMock()
        mock_empty.count = AsyncMock(return_value=0)

        mock_company_link = AsyncMock()
        mock_company_link.count = AsyncMock(return_value=1)
        mock_company_link.get_attribute = AsyncMock(
            return_value="/company/test-company/"
        )

        def locator_side_effect(selector):
            mock = AsyncMock()
            if "/company/" in selector:
                mock.first = mock_company_link
            else:
                mock.first = mock_empty
            return mock

        mock_item.locator = MagicMock(side_effect=locator_side_effect)

        result = await ProfileScraper._parse_experience_item(mock_item)

        assert result is not None
        assert result.title == ""
        assert result.company_id == "test-company"

    @pytest.mark.asyncio
    async def test_parse_item_returns_none_when_empty(self):
        """Test returns None when no title or company found."""
        mock_item = AsyncMock()

        mock_empty = AsyncMock()
        mock_empty.count = AsyncMock(return_value=0)

        def locator_side_effect(selector):
            mock = AsyncMock()
            mock.first = mock_empty
            return mock

        mock_item.locator = MagicMock(side_effect=locator_side_effect)

        result = await ProfileScraper._parse_experience_item(mock_item)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_item_year_only_date(self):
        """Test parsing item with year-only date format."""
        mock_item = AsyncMock()

        mock_title_elem = AsyncMock()
        mock_title_elem.count = AsyncMock(return_value=1)
        mock_title_elem.text_content = AsyncMock(return_value="Engineer")

        mock_empty = AsyncMock()
        mock_empty.count = AsyncMock(return_value=0)

        mock_date_elem = AsyncMock()
        mock_date_elem.count = AsyncMock(return_value=1)
        mock_date_elem.text_content = AsyncMock(return_value="2018 - 2020")

        def locator_side_effect(selector):
            mock = AsyncMock()
            if "t-bold" in selector and "aria-hidden" in selector:
                mock.first = mock_title_elem
            elif "pvs-entity__caption-wrapper" in selector:
                mock.first = mock_date_elem
            else:
                mock.first = mock_empty
            return mock

        mock_item.locator = MagicMock(side_effect=locator_side_effect)

        result = await ProfileScraper._parse_experience_item(mock_item)

        assert result is not None
        assert result.start_date == "2018"

    @pytest.mark.asyncio
    async def test_parse_item_full_month_name(self):
        """Test parsing item with full month name."""
        mock_item = AsyncMock()

        mock_title_elem = AsyncMock()
        mock_title_elem.count = AsyncMock(return_value=1)
        mock_title_elem.text_content = AsyncMock(return_value="Developer")

        mock_empty = AsyncMock()
        mock_empty.count = AsyncMock(return_value=0)

        mock_date_elem = AsyncMock()
        mock_date_elem.count = AsyncMock(return_value=1)
        mock_date_elem.text_content = AsyncMock(return_value="September 2021 - Present")

        def locator_side_effect(selector):
            mock = AsyncMock()
            if "t-bold" in selector and "aria-hidden" in selector:
                mock.first = mock_title_elem
            elif "pvs-entity__caption-wrapper" in selector:
                mock.first = mock_date_elem
            else:
                mock.first = mock_empty
            return mock

        mock_item.locator = MagicMock(side_effect=locator_side_effect)

        result = await ProfileScraper._parse_experience_item(mock_item)

        assert result is not None
        assert result.start_date == "September 2021"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_linkedin_experience_extraction(self):
        """Integration test for extracting experience from a real LinkedIn profile."""
        async with Service() as service:
            session = await service.launch_browser()
            page = await session._setup_page()
            profile_id = "jamesskelt"
            profile_url = f"https://www.linkedin.com/in/{profile_id}"
            await navigate_to_linkedin_url(page, profile_url)

            experience = await ProfileScraper.extract_profile_experience(page)
            print(f"Extracted {len(experience)} experiences:", flush=True)
            for exp in experience:
                print(exp, flush=True)

            assert experience is not None
            assert len(experience) > 0
            # Check first experience has expected fields
            assert experience[0].title != ""
            assert experience[0].company_id is not None


@pytest.mark.unit
class TestProfileExperienceModel:
    """Tests for ProfileExperience model"""

    def test_default_values(self):
        """Test ProfileExperience has correct defaults."""
        exp = ProfileExperience()
        assert exp.title == ""
        assert exp.company_id is None
        assert exp.start_date is None

    def test_with_all_fields(self):
        """Test ProfileExperience with all fields set."""
        exp = ProfileExperience(
            title="CEO",
            company_id="startup-inc",
            start_date="Jan 2015",
        )
        assert exp.title == "CEO"
        assert exp.company_id == "startup-inc"
        assert exp.start_date == "Jan 2015"

    def test_partial_fields(self):
        """Test ProfileExperience with partial fields."""
        exp = ProfileExperience(title="Intern")
        assert exp.title == "Intern"
        assert exp.company_id is None
        assert exp.start_date is None
