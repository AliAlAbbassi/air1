import pytest
import asyncio
import pytest_asyncio
from air1.services.linkedin.repo import (
    save_lead_complete,
    insert_linkedin_profile,
    get_linkedin_profile_by_username,
)
from air1.services.linkedin.service import extract_username_from_linkedin_url
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile
from air1.db.db import init_pool, close_pool


@pytest_asyncio.fixture
async def setup_db():
    """Initialize database pool for tests."""
    await init_pool()
    yield
    await close_pool()


@pytest.mark.asyncio
async def test_save_lead_complete(setup_db):
    """Test saving a complete lead with profile and company."""
    lead = Lead(
        first_name="John",
        full_name="John Doe",
        email="john.doe@example.com",
        phone_number="+1234567890"
    )

    profile = LinkedinProfile(
        profile_id="johndoe123",
        first_name="John",
        full_name="John Doe",
        headline="Software Engineer at Tech Corp",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/johndoe123",
        email="john.doe@example.com",
        phone_number="+1234567890",
        about="Experienced software engineer"
    )

    username = "techcorp"
    title = "TechCorp Inc"

    success, lead_id = await save_lead_complete(
        lead, profile, username, title
    )

    assert success is True
    assert lead_id is not None
    print(f"Successfully saved lead with ID: {lead_id}")


@pytest.mark.asyncio
async def test_save_lead_without_company(setup_db):
    """Test saving a lead without company association."""
    lead = Lead(
        first_name="Jane",
        full_name="Jane Smith",
        email="jane.smith@example.com",
        phone_number="+9876543210"
    )

    profile = LinkedinProfile(
        profile_id="janesmith456",
        first_name="Jane",
        full_name="Jane Smith",
        headline="Product Manager",
        location="New York, NY",
        linkedin_url="https://linkedin.com/in/janesmith456",
        email="jane.smith@example.com",
        phone_number="+9876543210",
        about="Product management professional"
    )

    success, lead_id = await save_lead_complete(lead, profile)

    assert success is True
    assert lead_id is not None
    print(f"Successfully saved lead without company with ID: {lead_id}")


# Username extraction tests
class TestExtractUsernameFromLinkedinUrl:
    """Test username extraction from LinkedIn URLs"""

    def test_basic_linkedin_url(self):
        url = "https://www.linkedin.com/in/johndoe/"
        assert extract_username_from_linkedin_url(url) == "johndoe"

    def test_linkedin_url_without_trailing_slash(self):
        url = "https://www.linkedin.com/in/johndoe"
        assert extract_username_from_linkedin_url(url) == "johndoe"

    def test_linkedin_url_with_query_params(self):
        url = "https://www.linkedin.com/in/johndoe?trk=profile"
        assert extract_username_from_linkedin_url(url) == "johndoe"

    def test_linkedin_url_with_hyphenated_username(self):
        url = "https://www.linkedin.com/in/john-doe-123/"
        assert extract_username_from_linkedin_url(url) == "john-doe-123"

    def test_empty_url(self):
        assert extract_username_from_linkedin_url("") == ""

    def test_invalid_url_without_in_segment(self):
        url = "https://www.linkedin.com/company/acme"
        assert extract_username_from_linkedin_url(url) == ""

    def test_malformed_url(self):
        url = "not-a-url"
        assert extract_username_from_linkedin_url(url) == ""


@pytest.mark.asyncio
async def test_save_profile_with_extracted_username(setup_db):
    """Test saving profile with username set from service layer"""
    lead = Lead(
        first_name="Test",
        full_name="Test User",
        email="test.username@example.com"
    )

    profile = LinkedinProfile(
        first_name="Test",
        full_name="Test User",
        username="test-username-123",  # Set directly in service layer
        location="Test City",
        headline="Test Engineer",
        about="Test about"
    )

    success, lead_id = await save_lead_complete(lead, profile, "https://linkedin.com/company/test", "test")

    assert success is True
    assert lead_id is not None

    # Verify username was extracted and stored
    retrieved = await get_linkedin_profile_by_username("test-username-123")
    assert retrieved is not None
    assert retrieved['username'] == "test-username-123"


@pytest.mark.asyncio
async def test_save_profile_with_username(setup_db):
    """Test saving profile with username set"""
    lead = Lead(
        first_name="Manual",
        full_name="Manual User",
        email="manual.user@example.com"
    )

    profile = LinkedinProfile(
        first_name="Manual",
        full_name="Manual User",
        username="manually-provided-username",
        location="Manual City",
        headline="Manual Engineer",
        about="Manual about"
    )

    success, lead_id = await save_lead_complete(lead, profile, "https://linkedin.com/company/manual", "manual")

    assert success is True
    assert lead_id is not None

    # Should find by the provided username
    retrieved = await get_linkedin_profile_by_username("manually-provided-username")
    assert retrieved is not None
    assert retrieved['username'] == "manually-provided-username"



@pytest.mark.asyncio
async def test_get_linkedin_profile_by_username_not_found(setup_db):
    """Test fetching non-existent LinkedIn profile by username"""
    result = await get_linkedin_profile_by_username("nonexistent-username")
    assert result is None


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_save_lead_complete(None))
    asyncio.run(test_save_lead_without_company(None))
    asyncio.run(test_save_profile_with_extracted_username(None))
    asyncio.run(test_save_profile_with_username(None))
    asyncio.run(test_get_linkedin_profile_by_username_not_found(None))
