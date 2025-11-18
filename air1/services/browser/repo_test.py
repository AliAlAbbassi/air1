import pytest
import asyncio
import pytest_asyncio
from air1.services.browser.repo import (
    save_lead_complete,
    get_linkedin_profile_by_username,
    insert_linkedin_company_member,
    get_company_members_by_username,
    get_company_member_by_profile_and_username,
    get_company_leads_by_headline,
    get_company_leads,
)
from air1.services.browser.linkedin_profile import Lead, LinkedinProfile
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
        phone_number="+1234567890",
    )

    profile = LinkedinProfile(
        first_name="John",
        full_name="John Doe",
        username="johndoe123",
        headline="Software Engineer at Tech Corp",
        location="San Francisco, CA",
        email="john.doe@example.com",
        phone_number="+1234567890",
        about="Experienced software engineer",
    )

    username = "techcorp"
    title = "TechCorp Inc"

    success, lead_id = await save_lead_complete(lead, profile, username, title)

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
        phone_number="+9876543210",
    )

    profile = LinkedinProfile(
        first_name="Jane",
        full_name="Jane Smith",
        username="janesmith456",
        headline="Product Manager",
        location="New York, NY",
        email="jane.smith@example.com",
        phone_number="+9876543210",
        about="Product management professional",
    )

    success, lead_id = await save_lead_complete(lead, profile)

    assert success is True
    assert lead_id is not None
    print(f"Successfully saved lead without company with ID: {lead_id}")


@pytest.mark.asyncio
async def test_save_profile_with_extracted_username(setup_db):
    """Test saving profile with username set from service layer"""
    lead = Lead(
        first_name="Test", full_name="Test User", email="test.username@example.com"
    )

    profile = LinkedinProfile(
        first_name="Test",
        full_name="Test User",
        username="test-username-123",  # Set directly in service layer
        location="Test City",
        headline="Test Engineer",
        about="Test about",
    )

    success, lead_id = await save_lead_complete(
        lead, profile, "https://linkedin.com/company/test", "test"
    )

    assert success is True
    assert lead_id is not None

    # Verify username was extracted and stored
    retrieved = await get_linkedin_profile_by_username("test-username-123")
    assert retrieved is not None
    assert retrieved["username"] == "test-username-123"


@pytest.mark.asyncio
async def test_save_profile_with_username(setup_db):
    """Test saving profile with username set"""
    lead = Lead(
        first_name="Manual", full_name="Manual User", email="manual.user@example.com"
    )

    profile = LinkedinProfile(
        first_name="Manual",
        full_name="Manual User",
        username="manually-provided-username",
        location="Manual City",
        headline="Manual Engineer",
        about="Manual about",
    )

    success, lead_id = await save_lead_complete(
        lead, profile, "https://linkedin.com/company/manual", "manual"
    )

    assert success is True
    assert lead_id is not None

    # Should find by the provided username
    retrieved = await get_linkedin_profile_by_username("manually-provided-username")
    assert retrieved is not None
    assert retrieved["username"] == "manually-provided-username"


@pytest.mark.asyncio
async def test_get_linkedin_profile_by_username_not_found(setup_db):
    """Test fetching non-existent LinkedIn profile by username"""
    result = await get_linkedin_profile_by_username("nonexistent-username")
    assert result is None


# Company member tests
@pytest.mark.asyncio
async def test_company_member_insertion_and_retrieval(setup_db):
    """Test company member insertion and retrieval by username"""
    import uuid
    unique_suffix = uuid.uuid4().hex[:8]

    # First create a lead and profile with unique identifiers
    lead = Lead(
        first_name="Company",
        full_name="Company Member Test",
        email=f"company.member.{unique_suffix}@example.com",
    )

    profile = LinkedinProfile(
        first_name="Company",
        full_name="Company Member Test",
        username=f"company-member-test-{unique_suffix}",
        location="Test City",
        headline="Test Engineer",
        about="Test about",
    )

    success, lead_id = await save_lead_complete(lead, profile)
    assert success is True
    assert lead_id is not None

    # Get the LinkedIn profile to get the profile ID
    retrieved_profile = await get_linkedin_profile_by_username(profile.username)
    assert retrieved_profile is not None
    linkedin_profile_id = retrieved_profile["linkedin_profile_id"]

    # Use unique company name
    company_username = f"testcorp-{unique_suffix}"

    # Insert company member
    await insert_linkedin_company_member(
        linkedin_profile_id, company_username, "Senior Engineer"
    )

    # Test retrieval by username - should only find our specific entry
    company_members = await get_company_members_by_username(company_username)
    assert len(company_members) == 1
    assert company_members[0]["username"] == company_username
    assert company_members[0]["title"] == "Senior Engineer"

    # Test retrieval by profile and username
    specific_member = await get_company_member_by_profile_and_username(
        linkedin_profile_id, company_username
    )
    assert specific_member is not None
    assert specific_member["username"] == company_username
    assert specific_member["title"] == "Senior Engineer"


@pytest.mark.asyncio
async def test_company_member_title_update_on_conflict(setup_db):
    """Test that company member title gets updated on conflict"""
    # First create a lead and profile
    lead = Lead(
        first_name="Update", full_name="Update Test", email="update.test@example.com"
    )

    profile = LinkedinProfile(
        first_name="Update",
        full_name="Update Test",
        username="update-test",
        location="Test City",
        headline="Test Engineer",
        about="Test about",
    )

    success, lead_id = await save_lead_complete(lead, profile)
    assert success is True

    retrieved_profile = await get_linkedin_profile_by_username("update-test")
    assert retrieved_profile is not None
    linkedin_profile_id = retrieved_profile["linkedin_profile_id"]

    # Insert company member with initial title
    await insert_linkedin_company_member(
        linkedin_profile_id, "updatecorp", "Junior Engineer"
    )

    # Insert again with updated title (should update due to conflict resolution)
    await insert_linkedin_company_member(
        linkedin_profile_id, "updatecorp", "Senior Engineer"
    )

    # Verify the title was updated
    specific_member = await get_company_member_by_profile_and_username(
        linkedin_profile_id, "updatecorp"
    )
    assert specific_member is not None
    assert specific_member["title"] == "Senior Engineer"


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
    lead1 = Lead(
        first_name="Multi1", full_name="Multi Test 1", email="multi1@example.com"
    )
    profile1 = LinkedinProfile(
        first_name="Multi1", full_name="Multi Test 1", username="multi-test-1"
    )

    lead2 = Lead(
        first_name="Multi2", full_name="Multi Test 2", email="multi2@example.com"
    )
    profile2 = LinkedinProfile(
        first_name="Multi2", full_name="Multi Test 2", username="multi-test-2"
    )

    success1, _ = await save_lead_complete(lead1, profile1)
    success2, _ = await save_lead_complete(lead2, profile2)
    assert success1 and success2

    # Get profile IDs
    retrieved_profile1 = await get_linkedin_profile_by_username("multi-test-1")
    retrieved_profile2 = await get_linkedin_profile_by_username("multi-test-2")

    assert retrieved_profile1 is not None
    assert retrieved_profile2 is not None
    profile_id1 = retrieved_profile1["linkedin_profile_id"]
    profile_id2 = retrieved_profile2["linkedin_profile_id"]

    # Both profiles work at the same company
    await insert_linkedin_company_member(profile_id1, "samecorp", "Engineer 1")
    await insert_linkedin_company_member(profile_id2, "samecorp", "Engineer 2")

    # Should find both when searching by company username
    company_members = await get_company_members_by_username("samecorp")
    assert len(company_members) == 2

    titles = [member["title"] for member in company_members]
    assert "Engineer 1" in titles
    assert "Engineer 2" in titles


@pytest.mark.asyncio
async def test_get_company_leads_by_headline(setup_db):
    """Test searching company leads by headline text"""
    # Create leads with different headlines
    lead1 = Lead(first_name="Alice", full_name="Alice Developer", email="alice@example.com")
    profile1 = LinkedinProfile(
        first_name="Alice",
        full_name="Alice Developer",
        username="alice-dev",
        headline="Senior Software Engineer with talent for innovation",
        location="SF"
    )

    lead2 = Lead(first_name="Bob", full_name="Bob Manager", email="bob@example.com")
    profile2 = LinkedinProfile(
        first_name="Bob",
        full_name="Bob Manager",
        username="bob-mgr",
        headline="Product Manager at TechCorp",
        location="NY"
    )

    # Save both leads
    success1, _ = await save_lead_complete(lead1, profile1, "techcorp", "Engineer")
    success2, _ = await save_lead_complete(lead2, profile2, "techcorp", "Manager")
    assert success1 and success2

    # Search for leads with "talent" in headline
    results = await get_company_leads_by_headline("techcorp", "talent")
    assert len(results) == 1
    assert results[0]["username"] == "alice-dev"
    assert "talent" in results[0]["headline"].lower()

    # Search for leads with "manager" in headline
    results = await get_company_leads_by_headline("techcorp", "manager")
    assert len(results) == 1
    assert results[0]["username"] == "bob-mgr"
    assert "manager" in results[0]["headline"].lower()


@pytest.mark.asyncio
async def test_get_company_leads(setup_db):
    """Test getting all leads for a company"""
    # Create multiple leads for the same company
    lead1 = Lead(first_name="John", full_name="John Smith", email="john@example.com")
    profile1 = LinkedinProfile(
        first_name="John",
        full_name="John Smith",
        username="john-smith",
        headline="Engineer",
        location="Seattle"
    )

    lead2 = Lead(first_name="Jane", full_name="Jane Doe", email="jane@example.com")
    profile2 = LinkedinProfile(
        first_name="Jane",
        full_name="Jane Doe",
        username="jane-doe",
        headline="Designer",
        location="Portland"
    )

    # Save leads for the same company
    success1, _ = await save_lead_complete(lead1, profile1, "designcorp", "Senior Engineer")
    success2, _ = await save_lead_complete(lead2, profile2, "designcorp", "Lead Designer")
    assert success1 and success2

    # Get all company leads
    results = await get_company_leads("designcorp")
    assert len(results) == 2

    usernames = [result["username"] for result in results]
    assert "john-smith" in usernames
    assert "jane-doe" in usernames


@pytest.mark.asyncio
async def test_get_company_leads_empty_company(setup_db):
    """Test getting leads for non-existent company"""
    results = await get_company_leads("nonexistent-company")
    assert results == []


@pytest.mark.asyncio
async def test_get_company_leads_by_headline_no_matches(setup_db):
    """Test searching company leads with no headline matches"""
    # Create a lead without the search term
    lead = Lead(first_name="Test", full_name="Test User", email="test@example.com")
    profile = LinkedinProfile(
        first_name="Test",
        full_name="Test User",
        username="test-user",
        headline="Software Developer",
        location="Austin"
    )

    success, _ = await save_lead_complete(lead, profile, "testcorp", "Developer")
    assert success

    # Search for non-matching term
    results = await get_company_leads_by_headline("testcorp", "marketing")
    assert results == []


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
    asyncio.run(test_get_company_leads_by_headline(None))
    asyncio.run(test_get_company_leads(None))
    asyncio.run(test_get_company_leads_empty_company(None))
    asyncio.run(test_get_company_leads_by_headline_no_matches(None))
