import pytest
from faker import Faker
from air1.services.linkedin.linkedin_profile import Lead, LinkedinProfile
from air1.services.linkedin.repo import insert_lead, insert_linkedin_profile, insert_linkedin_company_member
from air1.db import db as db_module

fake = Faker()

pytestmark = pytest.mark.asyncio


@pytest.mark.integration
class TestRepositoryIntegration:
    """Integration tests for repository functions with real database."""

    async def test_insert_lead_new(self, test_db, clean_db):
        """Test inserting a new lead."""
        db_module.pool = test_db

        lead = Lead(
            first_name=fake.first_name(),
            full_name=fake.name(),
            email=fake.email(),
            phone_number=fake.phone_number()
        )

        success, lead_id = await insert_lead(lead)

        assert success is True
        assert lead_id is not None
        assert isinstance(lead_id, int)

        # Verify the lead was inserted
        async with test_db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM lead WHERE lead_id = $1", lead_id
            )
            assert result is not None
            assert result['email'] == lead.email
            assert result['first_name'] == lead.first_name
            assert result['full_name'] == lead.full_name

    async def test_insert_lead_duplicate_email(self, test_db, clean_db):
        """Test upserting a lead with duplicate email."""
        db_module.pool = test_db

        email = fake.email()
        lead1 = Lead(
            first_name="John",
            full_name="John Doe",
            email=email,
            phone_number="123456789"
        )

        lead2 = Lead(
            first_name="Jane",
            full_name="Jane Smith",
            email=email,  # Same email
            phone_number="987654321"
        )

        success1, lead_id1 = await insert_lead(lead1)
        success2, lead_id2 = await insert_lead(lead2)

        assert success1 is True
        assert success2 is True
        assert lead_id1 == lead_id2  # Should be the same lead

        # Verify the lead was updated correctly
        async with test_db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM lead WHERE lead_id = $1", lead_id1
            )
            # Should keep first_name from lead1 (coalesce logic)
            assert result['first_name'] == "John"
            assert result['full_name'] == "John Doe"
            # Phone should be from lead1 as well
            assert result['phone_number'] == "123456789"

    async def test_insert_linkedin_profile(self, test_db, clean_db):
        """Test inserting a LinkedIn profile."""
        db_module.pool = test_db

        # First create a lead
        lead = Lead(
            first_name=fake.first_name(),
            full_name=fake.name(),
            email=fake.email()
        )
        success, lead_id = await insert_lead(lead)
        assert success is True

        # Create LinkedIn profile
        profile = LinkedinProfile(
            first_name=lead.first_name,
            full_name=lead.full_name,
            email=lead.email,
            linkedin_url=f"https://linkedin.com/in/{fake.user_name()}",
            location=fake.city(),
            headline=fake.job(),
            about=fake.text(max_nb_chars=200)
        )

        profile_id = await insert_linkedin_profile(profile, lead_id)

        assert profile_id is not None
        assert isinstance(profile_id, int)

        # Verify the profile was inserted
        async with test_db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM linkedin_profile WHERE linkedin_profile_id = $1", profile_id
            )
            assert result is not None
            assert result['lead_id'] == lead_id
            assert result['linkedin_url'] == profile.linkedin_url
            assert result['location'] == profile.location

    async def test_insert_linkedin_company_member(self, test_db, clean_db):
        """Test inserting a LinkedIn company member."""
        db_module.pool = test_db

        # Create lead and profile
        lead = Lead(
            first_name=fake.first_name(),
            full_name=fake.name(),
            email=fake.email()
        )
        success, lead_id = await insert_lead(lead)

        profile = LinkedinProfile(
            first_name=lead.first_name,
            full_name=lead.full_name,
            email=lead.email,
            linkedin_url=f"https://linkedin.com/in/{fake.user_name()}"
        )
        profile_id = await insert_linkedin_profile(profile, lead_id)

        # Insert company member
        username = fake.user_name()
        title = fake.company()

        await insert_linkedin_company_member(profile_id, username, title)

        # Verify insertion
        async with test_db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM linkedin_company_members WHERE linkedin_profile_id = $1",
                profile_id
            )
            assert result is not None
            assert result['username'] == username
            assert result['title'] == title

    async def test_full_workflow(self, test_db, clean_db):
        """Test the complete workflow from lead to company member."""
        db_module.pool = test_db

        # Create multiple leads with profiles
        num_leads = 3
        for _ in range(num_leads):
            lead = Lead(
                first_name=fake.first_name(),
                full_name=fake.name(),
                email=fake.email(),
                phone_number=fake.phone_number()
            )

            success, lead_id = await insert_lead(lead)
            assert success is True

            profile = LinkedinProfile(
                first_name=lead.first_name,
                full_name=lead.full_name,
                email=lead.email,
                linkedin_url=f"https://linkedin.com/in/{fake.user_name()}",
                location=fake.city(),
                headline=fake.job(),
                about=fake.text(max_nb_chars=200)
            )

            profile_id = await insert_linkedin_profile(profile, lead_id)
            assert profile_id is not None

            # Add multiple companies for each profile
            for _ in range(2):
                await insert_linkedin_company_member(
                    profile_id,
                    f"https://linkedin.com/company/{fake.company()}",
                    fake.company()
                )

        # Verify the data
        async with test_db.acquire() as conn:
            lead_count = await conn.fetchval("SELECT COUNT(*) FROM lead")
            profile_count = await conn.fetchval("SELECT COUNT(*) FROM linkedin_profile")
            company_count = await conn.fetchval("SELECT COUNT(*) FROM linkedin_company_members")

            assert lead_count == num_leads
            assert profile_count == num_leads
            assert company_count == num_leads * 2  # 2 companies per profile