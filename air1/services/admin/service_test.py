"""Integration tests for admin service functions.

These tests run against the real database (Docker localhost).

Run with:
    pytest air1/services/admin/service_test.py -v -s --use-real-db
"""

import pytest
import uuid

from air1.db.prisma_client import get_prisma
from air1.services.admin.service import AdminService, AdminError


@pytest.fixture
def service():
    """Create admin service instance."""
    return AdminService(base_url="http://test.example.com")


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


class TestAdminServiceAuthorization:
    """Tests for admin service authorization."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_require_admin_access_owner(self, service, test_agency_with_owner):
        """Test that owner has admin access."""
        user_id = test_agency_with_owner["user_id"]
        
        result = await service.require_admin_access(user_id)
        
        assert result.success is True
        assert result.data is not None
        assert result.data["agency_id"] == test_agency_with_owner["agency_id"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_require_admin_access_non_member(self, service):
        """Test that non-member is denied access."""
        result = await service.require_admin_access(999999999)
        
        assert result.success is False
        assert result.error == AdminError.FORBIDDEN

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_user_agency_context(self, service, test_agency_with_owner):
        """Test getting agency context for a user."""
        user_id = test_agency_with_owner["user_id"]
        
        context = await service.get_user_agency_context(user_id)
        
        assert context is not None
        assert context["agency_id"] == test_agency_with_owner["agency_id"]
        assert context["role"] == "owner"


class TestTeamManagement:
    """Tests for team management service functions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_team_members(self, service, test_agency_with_owner):
        """Test getting team members."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.get_team_members(agency_id)
        
        assert result.success is True
        assert "members" in result.data
        assert "usedSeats" in result.data
        assert len(result.data["members"]) >= 1  # At least the owner

    @pytest.mark.asyncio
    @pytest.mark.integration
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
    @pytest.mark.integration
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
    @pytest.mark.integration
    async def test_invite_team_member_invalid_role(self, service, test_agency_with_owner):
        """Test inviting with invalid role."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=10,
            email=f"role-{uuid.uuid4().hex[:8]}@test.com",
            role="superadmin",  # Invalid role
        )
        
        assert result.success is False
        assert result.error == AdminError.VALIDATION_ERROR

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invite_team_member_duplicate(self, service, test_agency_with_owner):
        """Test inviting same email twice."""
        agency_id = test_agency_with_owner["agency_id"]
        email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
        
        # First invite should succeed
        result1 = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=10,
            email=email,
            role="manager",
        )
        assert result1.success is True
        
        # Second invite should fail
        result2 = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=10,
            email=email,
            role="admin",
        )
        assert result2.success is False
        assert result2.error == AdminError.ALREADY_INVITED

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invite_team_member_seat_limit(self, service, test_agency_with_owner):
        """Test inviting when seat limit reached."""
        agency_id = test_agency_with_owner["agency_id"]
        
        # Set total_seats to 1 (already used by owner)
        result = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=1,  # Owner already uses 1 seat
            email=f"limit-{uuid.uuid4().hex[:8]}@test.com",
            role="manager",
        )
        
        assert result.success is False
        assert result.error == AdminError.SEAT_LIMIT_REACHED

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_member_role(self, service, test_agency_with_owner):
        """Test updating a member's role."""
        agency_id = test_agency_with_owner["agency_id"]
        
        # First invite a member
        invite_result = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=10,
            email=f"role-update-{uuid.uuid4().hex[:8]}@test.com",
            role="manager",
        )
        member_id = int(invite_result.data["memberID"])
        
        # Update role
        result = await service.update_member_role(
            agency_id=agency_id,
            member_id=member_id,
            new_role="admin",
        )
        
        assert result.success is True
        assert result.data["role"] == "admin"

    @pytest.mark.asyncio
    @pytest.mark.integration
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
    @pytest.mark.integration
    async def test_remove_team_member(self, service, test_agency_with_owner):
        """Test removing a team member."""
        agency_id = test_agency_with_owner["agency_id"]
        
        # First invite a member
        invite_result = await service.invite_team_member(
            agency_id=agency_id,
            total_seats=10,
            email=f"remove-{uuid.uuid4().hex[:8]}@test.com",
            role="manager",
        )
        member_id = int(invite_result.data["memberID"])
        
        # Remove member
        result = await service.remove_team_member(agency_id, member_id)
        
        assert result.success is True
        assert "message" in result.data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_remove_owner_fails(self, service, test_agency_with_owner):
        """Test that removing owner fails."""
        agency_id = test_agency_with_owner["agency_id"]
        member_id = test_agency_with_owner["member_id"]
        
        result = await service.remove_team_member(agency_id, member_id)
        
        assert result.success is False
        assert result.error == AdminError.CANNOT_REMOVE_OWNER


class TestClientManagement:
    """Tests for client management service functions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
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
    @pytest.mark.integration
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
    @pytest.mark.integration
    async def test_create_client_invalid_plan(self, service, test_agency_with_owner):
        """Test creating client with invalid plan."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.create_client(
            agency_id=agency_id,
            name="Bad Plan Corp",
            admin_email=f"plan-{uuid.uuid4().hex[:8]}@test.com",
            plan="ultimate",  # Invalid
        )
        
        assert result.success is False
        assert result.error == AdminError.VALIDATION_ERROR

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_clients(self, service, test_agency_with_owner):
        """Test getting all clients."""
        agency_id = test_agency_with_owner["agency_id"]
        
        # Create some clients
        await service.create_client(
            agency_id, "Client A", f"a-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        await service.create_client(
            agency_id, "Client B", f"b-{uuid.uuid4().hex[:8]}@test.com", "pro"
        )
        
        result = await service.get_clients(agency_id)
        
        assert result.success is True
        assert "clients" in result.data
        assert "total" in result.data
        assert result.data["total"] >= 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_clients_with_search(self, service, test_agency_with_owner):
        """Test searching clients."""
        agency_id = test_agency_with_owner["agency_id"]
        unique_name = f"SearchMe{uuid.uuid4().hex[:8]}"
        
        await service.create_client(
            agency_id, unique_name, f"search-{uuid.uuid4().hex[:8]}@test.com", "pro"
        )
        
        result = await service.get_clients(agency_id, search=unique_name[:10])
        
        assert result.success is True
        assert result.data["total"] >= 1
        assert any(unique_name in c["name"] for c in result.data["clients"])

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_client_detail(self, service, test_agency_with_owner):
        """Test getting client details."""
        agency_id = test_agency_with_owner["agency_id"]
        
        create_result = await service.create_client(
            agency_id, "Detail Client", f"detail-{uuid.uuid4().hex[:8]}@test.com", "enterprise"
        )
        client_id = int(create_result.data["clientID"])
        
        result = await service.get_client(agency_id, client_id)
        
        assert result.success is True
        assert result.data["name"] == "Detail Client"
        assert result.data["plan"] == "enterprise"
        assert "stats" in result.data
        assert "team" in result.data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_client_not_found(self, service, test_agency_with_owner):
        """Test getting non-existent client."""
        agency_id = test_agency_with_owner["agency_id"]
        
        result = await service.get_client(agency_id, 999999999)
        
        assert result.success is False
        assert result.error == AdminError.NOT_FOUND

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_client(self, service, test_agency_with_owner):
        """Test updating client."""
        agency_id = test_agency_with_owner["agency_id"]
        
        create_result = await service.create_client(
            agency_id, "Update Client", f"update-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        client_id = int(create_result.data["clientID"])
        
        result = await service.update_client(
            agency_id=agency_id,
            client_id=client_id,
            name="Updated Client Name",
            plan="pro",
        )
        
        assert result.success is True
        assert result.data["name"] == "Updated Client Name"
        assert result.data["plan"] == "pro"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_remove_client(self, service, test_agency_with_owner):
        """Test removing client."""
        agency_id = test_agency_with_owner["agency_id"]
        
        create_result = await service.create_client(
            agency_id, "Remove Client", f"remove-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        client_id = int(create_result.data["clientID"])
        
        result = await service.remove_client(agency_id, client_id)
        
        assert result.success is True
        
        # Verify removed
        get_result = await service.get_client(agency_id, client_id)
        assert get_result.success is False
        assert get_result.error == AdminError.NOT_FOUND

    @pytest.mark.asyncio
    @pytest.mark.integration
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

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_impersonate_nonexistent_client(self, service, test_agency_with_owner):
        """Test impersonating non-existent client."""
        agency_id = test_agency_with_owner["agency_id"]
        member_id = test_agency_with_owner["member_id"]
        
        result = await service.impersonate_client(
            agency_id=agency_id,
            member_id=member_id,
            client_id=999999999,
        )
        
        assert result.success is False
        assert result.error == AdminError.NOT_FOUND

