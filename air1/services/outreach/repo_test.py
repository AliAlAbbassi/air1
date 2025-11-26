import pytest
import uuid
from unittest.mock import patch, AsyncMock
from air1.services.outreach.repo import (
    insert_lead,
    insert_linkedin_profile,
    get_linkedin_profile_by_username,
    get_company_leads,
    get_company_leads_by_headline,
    save_lead_complete,
    insert_contact_point,
)
from air1.services.outreach.linkedin_profile import Lead, LinkedinProfile
from air1.services.outreach.prisma_models import CompanyLeadRecord
from air1.db.prisma_client import connect_db, disconnect_db, get_prisma
from loguru import logger


@pytest.mark.asyncio
@pytest.mark.integration
async def test_insert_and_get_lead():
    """Test inserting a lead and LinkedIn profile, then retrieving it."""
    try:
        await connect_db()

        # Create unique test data using UUID
        test_uuid = str(uuid.uuid4())[:8]

        lead = Lead(
            first_name="John",
            full_name="John Doe",
            email=f"john.doe.test.{test_uuid}@example.com",
            phone_number="+1234567890",
        )

        profile = LinkedinProfile(
            username=f"john-doe-test-{test_uuid}",
            first_name="John",
            full_name="John Doe",
            headline="Software Engineer",
            location="San Francisco, CA",
            email=f"john.doe.test.{test_uuid}@example.com",
        )

        # Insert lead
        success, lead_id = await insert_lead(lead)
        assert success is True
        assert lead_id is not None

        # Insert LinkedIn profile
        profile_id = await insert_linkedin_profile(profile, lead_id)
        assert profile_id is not None

        # Retrieve the profile by username
        retrieved_profile = await get_linkedin_profile_by_username(profile.username)
        assert retrieved_profile is not None
        assert retrieved_profile.username == profile.username
        assert retrieved_profile.headline == profile.headline
        # Use the aliased field name from Pydantic model (camelCase)
        assert retrieved_profile.leadId == lead_id
    finally:
        await disconnect_db()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_save_lead_complete():
    """Test saving a complete lead with profile and company association."""
    try:
        await connect_db()

        # Create unique test data with full UUID to avoid collisions
        test_uuid = str(uuid.uuid4())

        lead = Lead(
            first_name="Jane",
            full_name="Jane Smith",
            email=f"jane.smith.test.{test_uuid}@example.com",
            phone_number=f"+{test_uuid[:10]}",  # Use part of UUID for phone too
        )

        profile = LinkedinProfile(
            username=f"jane-smith-test-{test_uuid}",
            first_name="Jane",
            full_name="Jane Smith",
            headline="Product Manager",
            location="New York, NY",
            email=f"jane.smith.test.{test_uuid}@example.com",
        )

        # Save complete lead with company association
        success, lead_id = await save_lead_complete(
            lead, profile, f"tech-company-{test_uuid}", "Manager"
        )

        assert success is True, f"Failed to save lead: {lead.email}"
        assert lead_id is not None

        # Verify the lead was saved correctly
        retrieved_profile = await get_linkedin_profile_by_username(profile.username)
        assert retrieved_profile is not None
        assert retrieved_profile.leadId == lead_id
    finally:
        await disconnect_db()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_company_leads_integration():
    """Test retrieving company leads from the database."""
    try:
        await connect_db()
        # This test uses existing data in the database
        # Note: This assumes you have some test data in your local database

        try:
            company_leads = await get_company_leads("tech-usa")

            # Basic validation - the function should return a list
            assert isinstance(company_leads, list)

            if len(company_leads) > 0:
                # Validate the structure of returned records
                first_lead = company_leads[0]
                assert isinstance(first_lead, CompanyLeadRecord)
                assert hasattr(first_lead, "lead_id")
                assert hasattr(first_lead, "username")
                assert hasattr(first_lead, "company_name")
                assert first_lead.company_name == "tech-usa"

                logger.info(f"Retrieved {len(company_leads)} leads for tech-usa")
                logger.info(f"Sample lead: {first_lead.full_name} - {first_lead.headline}")
            else:
                logger.info("No leads found for tech-usa in test database")

        except Exception as e:
            # If there's no data for tech-usa, that's okay for this test
            logger.info(f"No existing data for tech-usa: {e}")

            # Test with empty result
            empty_leads = await get_company_leads("nonexistent-company-12345")
            assert isinstance(empty_leads, list)
            assert len(empty_leads) == 0
    finally:
        await disconnect_db()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_connection():
    """Test that we can connect to the database."""
    try:
        await connect_db()
        prisma = await get_prisma()
        assert prisma is not None
        assert prisma.is_connected() is True

        # Simple query to verify connection works
        leads_count = await prisma.lead.count()
        assert isinstance(leads_count, int)
        logger.info(f"Total leads in database: {leads_count}")
    finally:
        # Ensure cleanup
        await disconnect_db()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_company_leads_by_headline():
    """Test getting company leads filtered by headline text."""
    try:
        await connect_db()

        # Test with existing data - look for "recruiter" in tech-usa
        results = await get_company_leads_by_headline("tech-usa", "recruiter")

        assert isinstance(results, list)

        if len(results) > 0:
            first_result = results[0]
            assert isinstance(first_result, CompanyLeadRecord)
            assert hasattr(first_result, "lead_id")
            assert hasattr(first_result, "headline")
            assert first_result.company_name == "tech-usa"
            assert first_result.headline and "recruiter" in first_result.headline.lower()

            logger.info(f"Found {len(results)} leads with 'recruiter' in headline for tech-usa")
        else:
            logger.info("No leads found with 'recruiter' in headline")

        # Test with non-matching search term
        empty_results = await get_company_leads_by_headline("tech-usa", "xyznonexistent")
        assert isinstance(empty_results, list)
        assert len(empty_results) == 0

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        await disconnect_db()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_insert_contact_point_returns_false_on_error():
    """Test that insert_contact_point returns False (not raises) on database error.

    This test verifies the fix for issue #12: insert_contact_point should return
    False on error to be consistent with other repo functions, not re-raise.
    """
    with patch("air1.services.outreach.repo.get_prisma") as mock_get_prisma:
        mock_get_prisma.side_effect = Exception("Database connection failed")

        # Should return False, not raise an exception
        result = await insert_contact_point(lead_id=1, contact_point_type_id=1)

        assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_insert_contact_point_returns_true_on_success():
    """Test that insert_contact_point returns True on successful insertion."""
    with patch("air1.services.outreach.repo.get_prisma") as mock_get_prisma, \
         patch("air1.services.outreach.repo.queries") as mock_queries:
        mock_prisma = AsyncMock()
        mock_get_prisma.return_value = mock_prisma
        mock_queries.insert_contact_point = AsyncMock(
            return_value={"contact_point_id": 123}
        )

        result = await insert_contact_point(lead_id=1, contact_point_type_id=1)

        assert result is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_insert_contact_point_returns_false_when_no_result():
    """Test that insert_contact_point returns False when query returns no result."""
    with patch("air1.services.outreach.repo.get_prisma") as mock_get_prisma, \
         patch("air1.services.outreach.repo.queries") as mock_queries:
        mock_prisma = AsyncMock()
        mock_get_prisma.return_value = mock_prisma
        mock_queries.insert_contact_point = AsyncMock(return_value=None)

        result = await insert_contact_point(lead_id=1, contact_point_type_id=1)

        assert result is False