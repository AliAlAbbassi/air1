import pytest
import uuid
from air1.services.outreach.repo import (
    insert_lead,
    insert_linkedin_profile,
    get_linkedin_profile_by_username,
    get_company_members_by_username,
    insert_linkedin_company_member,
    get_company_member_by_profile_and_username
)
from air1.services.outreach.linkedin_profile import Lead, LinkedinProfile
from air1.db.prisma_client import connect_db, disconnect_db, get_prisma

@pytest.mark.asyncio
@pytest.mark.integration
async def test_upsert_lead():
    """Test that inserting a lead with an existing email updates the record."""
    try:
        await connect_db()
        test_uuid = str(uuid.uuid4())[:8]
        email = f"upsert.test.{test_uuid}@example.com"

        # 1. Insert initial lead
        lead_v1 = Lead(
            first_name="Original",
            full_name="Original Name",
            email=email,
            phone_number="+1111111111"
        )
        success, lead_id = await insert_lead(lead_v1)
        assert success is True
        assert lead_id is not None

        # 2. Insert updated lead (same email)
        lead_v2 = Lead(
            first_name="Updated",
            full_name="Updated Name",
            email=email,
            phone_number="+2222222222"
        )
        success_v2, lead_id_v2 = await insert_lead(lead_v2)
        
        # 3. Verify it's the same ID
        assert success_v2 is True
        assert lead_id_v2 == lead_id

        # 4. Verify data was updated in DB
        # We don't have a get_lead_by_id in repo yet, but we can check via profile or raw prisma
        prisma = await get_prisma()
        db_lead = await prisma.lead.find_unique(where={'leadId': int(lead_id)})
        
        assert db_lead is not None
        assert db_lead.firstName == "Updated"
        assert db_lead.fullName == "Updated Name"
        assert db_lead.phoneNumber == "+2222222222"
    finally:
        await disconnect_db()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_upsert_linkedin_profile():
    """Test that inserting a profile with an existing username updates the record."""
    try:
        await connect_db()
        test_uuid = str(uuid.uuid4())[:8]
        username = f"upsert-profile-{test_uuid}"
        
        # Setup a lead first
        lead = Lead(first_name="Test", full_name="Test User", email=f"test.{test_uuid}@example.com")
        _, lead_id = await insert_lead(lead)

        # 1. Insert initial profile
        profile_v1 = LinkedinProfile(
            username=username,
            headline="Junior Developer",
            location="Remote",
            about="Original bio"
        )
        pid1 = await insert_linkedin_profile(profile_v1, lead_id)
        assert pid1 is not None

        # 2. Insert updated profile (same username)
        profile_v2 = LinkedinProfile(
            username=username,
            headline="Senior Developer", # Changed
            location="New York",         # Changed
            about="Updated bio"          # Changed
        )
        pid2 = await insert_linkedin_profile(profile_v2, lead_id)
        
        # 3. Verify IDs match
        assert pid2 == pid1

        # 4. Fetch and verify update
        fetched = await get_linkedin_profile_by_username(username)
        assert fetched is not None
        assert fetched.headline == "Senior Developer"
        assert fetched.location == "New York"
        assert fetched.about == "Updated bio"
    finally:
        await disconnect_db()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_company_members_crud():
    """Test inserting and retrieving company members."""
    try:
        await connect_db()
        test_uuid = str(uuid.uuid4())[:8]
        username = f"company-tester-{test_uuid}"
        company_name = f"company-{test_uuid}"
        
        # Setup lead & profile
        lead = Lead(first_name="Company", full_name="Tester", email=f"cm.{test_uuid}@example.com")
        _, lead_id = await insert_lead(lead)
        profile = LinkedinProfile(username=username, headline="Worker")
        profile_id = await insert_linkedin_profile(profile, lead_id)

        # 1. Insert Company Member
        await insert_linkedin_company_member(profile_id, company_name, title="Software Engineer")

        # 2. Retrieve by specific profile and company
        member = await get_company_member_by_profile_and_username(profile_id, company_name)
        assert member is not None
        assert member.username == company_name
        assert member.title == "Software Engineer"
        assert member.linkedinProfileId == profile_id

        # 3. Retrieve all members of this company
        # (Should find at least the one we just added)
        members = await get_company_members_by_username(company_name)
        assert len(members) >= 1
        found = next((m for m in members if m.linkedinProfileId == profile_id), None)
        assert found is not None
        assert found.title == "Software Engineer"

        # 4. Test Upsert on Company Member (Update Title)
        await insert_linkedin_company_member(profile_id, company_name, title="CTO")
        
        updated_member = await get_company_member_by_profile_and_username(profile_id, company_name)
        assert updated_member.title == "CTO"
    finally:
        await disconnect_db()
