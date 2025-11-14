import pytest
import asyncio
import pytest_asyncio
from air1.services.linkedin.repo import (
    save_lead_complete,
    insert_linkedin_profile,
    get_linkedin_profile_by_username,
    insert_linkedin_company_member,
    get_company_members_by_username,
    get_company_member_by_profile_and_username,
)
from air1.services.linkedin.service import extract_username_from_linkedin_url, extract_company_id_from_linkedin_url
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


# Company ID extraction tests
class TestExtractCompanyIdFromLinkedinUrl:
    """Test company ID extraction from LinkedIn company URLs"""

    def test_basic_company_url(self):
        url = "https://www.linkedin.com/company/acme/"
        assert extract_company_id_from_linkedin_url(url) == "acme"

    def test_company_url_without_trailing_slash(self):
        url = "https://www.linkedin.com/company/acme"
        assert extract_company_id_from_linkedin_url(url) == "acme"

    def test_company_url_with_query_params(self):
        url = "https://www.linkedin.com/company/acme?trk=company"
        assert extract_company_id_from_linkedin_url(url) == "acme"

    def test_company_url_with_hyphenated_id(self):
        url = "https://www.linkedin.com/company/acme-corp-123/"
        assert extract_company_id_from_linkedin_url(url) == "acme-corp-123"

    def test_empty_company_url(self):
        assert extract_company_id_from_linkedin_url("") == ""

    def test_invalid_url_without_company_segment(self):
        url = "https://www.linkedin.com/in/johndoe"
        assert extract_company_id_from_linkedin_url(url) == ""

    def test_malformed_company_url(self):
        url = "not-a-url"
        assert extract_company_id_from_linkedin_url(url) == ""


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


# Company member tests
@pytest.mark.asyncio
async def test_company_member_insertion_and_retrieval(setup_db):
    """Test company member insertion and retrieval by username"""
    # First create a lead and profile
    lead = Lead(
        first_name="Company",
        full_name="Company Member Test",
        email="company.member@example.com"
    )

    profile = LinkedinProfile(
        first_name="Company",
        full_name="Company Member Test",
        username="company-member-test",
        location="Test City",
        headline="Test Engineer",
        about="Test about"
    )

    success, lead_id = await save_lead_complete(lead, profile)
    assert success is True
    assert lead_id is not None

    # Get the LinkedIn profile to get the profile ID
    retrieved_profile = await get_linkedin_profile_by_username("company-member-test")
    assert retrieved_profile is not None
    linkedin_profile_id = retrieved_profile['linkedin_profile_id']

    # Insert company member
    await insert_linkedin_company_member(linkedin_profile_id, "testcorp", "Senior Engineer")

    # Test retrieval by username
    company_members = await get_company_members_by_username("testcorp")
    assert len(company_members) == 1
    assert company_members[0]['username'] == "testcorp"
    assert company_members[0]['title'] == "Senior Engineer"

    # Test retrieval by profile and username
    specific_member = await get_company_member_by_profile_and_username(linkedin_profile_id, "testcorp")
    assert specific_member is not None
    assert specific_member['username'] == "testcorp"
    assert specific_member['title'] == "Senior Engineer"


@pytest.mark.asyncio
async def test_company_member_title_update_on_conflict(setup_db):
    """Test that company member title gets updated on conflict"""
    # First create a lead and profile
    lead = Lead(
        first_name="Update",
        full_name="Update Test",
        email="update.test@example.com"
    )

    profile = LinkedinProfile(
        first_name="Update",
        full_name="Update Test",
        username="update-test",
        location="Test City",
        headline="Test Engineer",
        about="Test about"
    )

    success, lead_id = await save_lead_complete(lead, profile)
    assert success is True

    retrieved_profile = await get_linkedin_profile_by_username("update-test")
    linkedin_profile_id = retrieved_profile['linkedin_profile_id']

    # Insert company member with initial title
    await insert_linkedin_company_member(linkedin_profile_id, "updatecorp", "Junior Engineer")

    # Insert again with updated title (should update due to conflict resolution)
    await insert_linkedin_company_member(linkedin_profile_id, "updatecorp", "Senior Engineer")

    # Verify the title was updated
    specific_member = await get_company_member_by_profile_and_username(linkedin_profile_id, "updatecorp")
    assert specific_member is not None
    assert specific_member['title'] == "Senior Engineer"


@pytest.mark.asyncio
async def test_get_company_members_empty_username(setup_db):
    """Test fetching company members with empty username"""
    result = await get_company_members_by_username("")
    assert result == []


@pytest.mark.asyncio
async def test_get_company_member_not_found(setup_db):
    """Test fetching non-existent company member"""
    result = await get_company_member_by_profile_and_username(99999, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_company_member_multiple_profiles_same_username(setup_db):
    """Test multiple profiles can be associated with same company username"""
    # Create two different profiles
    lead1 = Lead(first_name="Multi1", full_name="Multi Test 1", email="multi1@example.com")
    profile1 = LinkedinProfile(first_name="Multi1", full_name="Multi Test 1", username="multi-test-1")

    lead2 = Lead(first_name="Multi2", full_name="Multi Test 2", email="multi2@example.com")
    profile2 = LinkedinProfile(first_name="Multi2", full_name="Multi Test 2", username="multi-test-2")

    success1, _ = await save_lead_complete(lead1, profile1)
    success2, _ = await save_lead_complete(lead2, profile2)
    assert success1 and success2

    # Get profile IDs
    retrieved_profile1 = await get_linkedin_profile_by_username("multi-test-1")
    retrieved_profile2 = await get_linkedin_profile_by_username("multi-test-2")

    profile_id1 = retrieved_profile1['linkedin_profile_id']
    profile_id2 = retrieved_profile2['linkedin_profile_id']

    # Both profiles work at the same company
    await insert_linkedin_company_member(profile_id1, "samecorp", "Engineer 1")
    await insert_linkedin_company_member(profile_id2, "samecorp", "Engineer 2")

    # Should find both when searching by company username
    company_members = await get_company_members_by_username("samecorp")
    assert len(company_members) == 2

    titles = [member['title'] for member in company_members]
    assert "Engineer 1" in titles
    assert "Engineer 2" in titles


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_save_lead_complete(None))
    asyncio.run(test_save_lead_without_company(None))
    asyncio.run(test_save_profile_with_extracted_username(None))
    asyncio.run(test_save_profile_with_username(None))
    asyncio.run(test_get_linkedin_profile_by_username_not_found(None))
    asyncio.run(test_company_member_insertion_and_retrieval(None))
    asyncio.run(test_company_member_title_update_on_conflict(None))
    asyncio.run(test_get_company_members_empty_username(None))
    asyncio.run(test_get_company_member_not_found(None))
    asyncio.run(test_company_member_multiple_profiles_same_username(None))
