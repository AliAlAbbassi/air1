import pytest
import asyncio
import pytest_asyncio
from air1.services.linkedin.repo import save_lead_complete
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

    company_url = "https://www.linkedin.com/company/techcorp/"
    company_name = "techcorp"

    success, lead_id = await save_lead_complete(
        lead, profile, company_url, company_name
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


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_save_lead_complete(None))
    asyncio.run(test_save_lead_without_company(None))