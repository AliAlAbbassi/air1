"""Integration tests for unified account service.

These tests run against the real database (Docker localhost).

Run with:
    pytest air1/services/account/service_test.py -v -s --use-real-db
"""

import pytest
import uuid

from air1.db.prisma_client import get_prisma
from air1.services.account import Service, AdminError


@pytest.fixture
def service():
    """Create service instance."""
    return Service(base_url="http://test.example.com")


@pytest.fixture
async def test_agency_with_owner(db_connection):
    """Create a test agency with an owner member and clean up after."""
    if not db_connection:
        pytest.skip("Database connection required")
    
    prisma = await get_prisma()
    
    # Create test user first
    user_email = f"owner-{uuid.uuid4().hex[:8]}@test.com"
    user_result = await prisma.query_raw(
        """
        INSERT INTO hodhod_user (email, clerk_id, auth_method, created_on, updated_on)
        VALUES ($1, $2, 'clerk', NOW(), NOW())
        RETURNING user_id, email, clerk_id
        """,
        user_email,
        f"clerk_{uuid.uuid4().hex}",
    )
    user = user_result[0]
    user_id = user["user_id"]
    
    # Create test agency
    agency_result = await prisma.query_raw(
        """
        INSERT INTO agency (name, total_seats, created_on, updated_on)
        VALUES ($1, $2, NOW(), NOW())
        RETURNING agency_id, name, total_seats
        """,
        f"Test Agency {uuid.uuid4().hex[:8]}",
        10,
    )
    agency = agency_result[0]
    agency_id = agency["agency_id"]
    
    # Create owner member
    member_result = await prisma.query_raw(
        """
        INSERT INTO agency_member (agency_id, user_id, email, name, role, status, invited_at, joined_at)
        VALUES ($1, $2, $3, $4, 'owner'::agency_role, 'active'::member_status, NOW(), NOW())
        RETURNING member_id, email, role, status
        """,
        agency_id,
        user_id,
        user_email,
        "Test Owner",
    )
    member = member_result[0]
    
    yield {
        "agency": agency,
        "user": user,
        "member": member,
        "agency_id": agency_id,
        "user_id": user_id,
        "member_id": member["member_id"],
    }
    
    # Cleanup
    try:
        await prisma.query_raw("DELETE FROM agency WHERE agency_id = $1", agency_id)
        await prisma.query_raw("DELETE FROM hodhod_user WHERE user_id = $1", user_id)
    except Exception:
        pass


# ============================================================================
# USER SERVICE TESTS
# ============================================================================


class TestUserService:
    """Tests for user account service methods."""

    @pytest.fixture
    def unique_clerk_id(self):
        """Generate a unique clerk_id for each test."""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @pytest.mark.asyncio
    async def test_get_or_create_account_creates_new_user(self, service, unique_clerk_id, db_connection):
        """Test creating account for new user."""
        if not db_connection:
            pytest.skip("Database connection required")
        email = f"{unique_clerk_id}@test.example.com"

        result = await service.get_or_create_account(
            clerk_id=unique_clerk_id,
            email=email,
        )

        assert result is not None
        assert result["clerk_id"] == unique_clerk_id
        assert result["email"] == email
        assert result["user_id"] is not None

    @pytest.mark.asyncio
    async def test_get_or_create_account_returns_existing_user(self, service, unique_clerk_id, db_connection):
        """Test getting account for existing user."""
        if not db_connection:
            pytest.skip("Database connection required")
        email = f"{unique_clerk_id}@test.example.com"

        # Create user first
        created = await service.get_or_create_account(
            clerk_id=unique_clerk_id,
            email=email,
        )
        assert created is not None
        original_user_id = created["user_id"]

        # Get same user again
        result = await service.get_or_create_account(
            clerk_id=unique_clerk_id,
            email=email,
        )

        assert result is not None
        assert result["user_id"] == original_user_id
        assert result["clerk_id"] == unique_clerk_id

    @pytest.mark.asyncio
    async def test_update_profile_success(self, service, unique_clerk_id, db_connection):
        """Test successful profile update."""
        if not db_connection:
            pytest.skip("Database connection required")
        email = f"{unique_clerk_id}@test.example.com"

        # Create user first
        await service.get_or_create_account(clerk_id=unique_clerk_id, email=email)

        # Update profile
        result = await service.update_profile(
            clerk_id=unique_clerk_id,
            first_name="Test",
            last_name="User",
            timezone="America/New_York",
            meeting_link="https://cal.com/test/30min",
        )

        assert result is True

        # Verify update
        account = await service.get_or_create_account(clerk_id=unique_clerk_id, email=email)
        assert account["first_name"] == "Test"
        assert account["last_name"] == "User"
        assert account["timezone"] == "America/New_York"
        assert account["meeting_link"] == "https://cal.com/test/30min"


# ============================================================================
# ADMIN SERVICE TESTS
# ============================================================================


class TestAdminAuthorization:
    """Tests for admin service authorization."""

    @pytest.mark.asyncio
    async def test_require_admin_access_owner(self, service, test_agency_with_owner):
        """Test that owner has admin access."""
        user_id = test_agency_with_owner["user_id"]
        
        result = await service.require_admin_access(user_id)
        
        assert result.success is True
        assert result.data is not None
        assert result.data["agency_id"] == test_agency_with_owner["agency_id"]

    @pytest.mark.asyncio
    async def test_require_admin_access_non_member(self, service, db_connection):
        """Test that non-member is denied access."""
        if not db_connection:
            pytest.skip("Database connection required")
        result = await service.require_admin_access(999999999)
        
        assert result.success is False
        assert result.error == AdminError.FORBIDDEN


class TestTeamManagement:
    """Tests for team management service methods."""

    @pytest.mark.asyncio
    async def test_get_team_members(self, service, test_agency_with_owner):
        """Test getting team members."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.get_team_members(agency_id)
        
        assert result.success is True
        assert "members" in result.data
        assert "usedSeats" in result.data
        assert len(result.data["members"]) >= 1

    @pytest.mark.asyncio
    async def test_invite_team_member_success(self, service, test_agency_with_owner):
        """Test inviting a new team member."""
        agency_id = test_agency_with_owner["agency_id"]
        email = f"invite-{uuid.uuid4().hex[:8]}@test.com"
        
        result = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=10,
            email=email,
            role="manager",
        )
        
        assert result.success is True
        assert result.data["email"] == email
        assert result.data["role"] == "manager"
        assert result.data["status"] == "pending"
        assert "memberID" in result.data

    @pytest.mark.asyncio
    async def test_invite_team_member_invalid_email(self, service, test_agency_with_owner):
        """Test inviting with invalid email."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=10,
            email="invalid-email",
            role="manager",
        )
        
        assert result.success is False
        assert result.error == AdminError.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_update_owner_role_fails(self, service, test_agency_with_owner):
        """Test that updating owner's role fails."""
        agency_id = test_agency_with_owner["agency_id"]
        member_id = test_agency_with_owner["member_id"]
        
        result = await service.update_member_role(
            agency_id=agency_id,
            member_id=member_id,
            new_role="admin",
        )
        
        assert result.success is False
        assert result.error == AdminError.CANNOT_CHANGE_OWNER_ROLE

    @pytest.mark.asyncio
    async def test_remove_owner_fails(self, service, test_agency_with_owner):
        """Test that removing owner fails."""
        agency_id = test_agency_with_owner["agency_id"]
        member_id = test_agency_with_owner["member_id"]
        
        result = await service.remove_team_member(agency_id, member_id)
        
        assert result.success is False
        assert result.error == AdminError.CANNOT_REMOVE_OWNER


class TestClientManagement:
    """Tests for client management service methods."""

    @pytest.mark.asyncio
    async def test_create_client_success(self, service, test_agency_with_owner):
        """Test creating a new client."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.create_client(
            agency_id=agency_id,
            name="New Client Corp",
            admin_email=f"client-{uuid.uuid4().hex[:8]}@test.com",
            plan="pro",
        )
        
        assert result.success is True
        assert result.data["name"] == "New Client Corp"
        assert result.data["plan"] == "pro"
        assert result.data["status"] == "onboarding"
        assert "inviteLink" in result.data
        assert result.data["inviteLink"].startswith("http://test.example.com/setup?token=")

    @pytest.mark.asyncio
    async def test_create_client_invalid_email(self, service, test_agency_with_owner):
        """Test creating client with invalid email."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.create_client(
            agency_id=agency_id,
            name="Bad Email Corp",
            admin_email="not-an-email",
            plan="starter",
        )
        
        assert result.success is False
        assert result.error == AdminError.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_get_client_not_found(self, service, test_agency_with_owner):
        """Test getting non-existent client."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.get_client(agency_id, 999999999)
        
        assert result.success is False
        assert result.error == AdminError.NOT_FOUND

    @pytest.mark.asyncio
    async def test_impersonate_client(self, service, test_agency_with_owner):
        """Test generating impersonation URL."""
        agency_id = test_agency_with_owner["agency_id"]
        member_id = test_agency_with_owner["member_id"]
        
        create_result = await service.create_client(
            agency_id, "Impersonate Client", f"imp-{uuid.uuid4().hex[:8]}@test.com", "pro"
        )
        client_id = int(create_result.data["clientID"])
        
        result = await service.impersonate_client(
            agency_id=agency_id,
            member_id=member_id,
            client_id=client_id,
        )
        
        assert result.success is True
        assert "impersonationUrl" in result.data
        assert result.data["impersonationUrl"].startswith("http://test.example.com/impersonate?token=")
        assert "expiresAt" in result.data

