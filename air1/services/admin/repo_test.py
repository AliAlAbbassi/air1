"""Integration tests for admin repo functions.

These tests run against the real database (Docker localhost).

Run with:
    pytest air1/services/admin/repo_test.py -v -s --use-real-db
"""

import pytest
import uuid

from air1.db.prisma_client import get_prisma
from air1.services.admin import repo


@pytest.fixture
async def test_agency(db_connection):
    """Create a test agency and clean up after."""
    if not db_connection:
        pytest.skip("Database connection required")
    
    prisma = await get_prisma()
    
    # Create test agency
    result = await prisma.query_raw(
        """
        INSERT INTO agency (name, total_seats, created_on, updated_on)
        VALUES ($1, $2, NOW(), NOW())
        RETURNING agency_id, name, total_seats
        """,
        f"Test Agency {uuid.uuid4().hex[:8]}",
        10,
    )
    agency = result[0]
    agency_id = agency["agency_id"]
    
    yield agency
    
    # Cleanup: Delete agency (cascades to members, clients, etc.)
    try:
        await prisma.query_raw(
            "DELETE FROM agency WHERE agency_id = $1",
            agency_id,
        )
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
async def test_user(db_connection):
    """Create a test user and clean up after."""
    if not db_connection:
        pytest.skip("Database connection required")
    
    prisma = await get_prisma()
    
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    result = await prisma.query_raw(
        """
        INSERT INTO hodhod_user (email, clerk_id, auth_method, created_on, updated_on)
        VALUES ($1, $2, 'clerk', NOW(), NOW())
        RETURNING user_id, email, clerk_id
        """,
        email,
        f"clerk_{uuid.uuid4().hex}",
    )
    user = result[0]
    user_id = user["user_id"]
    
    yield user
    
    # Cleanup
    try:
        await prisma.query_raw(
            "DELETE FROM hodhod_user WHERE user_id = $1",
            user_id,
        )
    except Exception:
        pass


class TestAgencyMemberRepo:
    """Tests for agency member repository functions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_insert_agency_member(self, test_agency):
        """Test inserting a new agency member."""
        agency_id = test_agency["agency_id"]
        email = f"member-{uuid.uuid4().hex[:8]}@example.com"
        
        result = await repo.insert_agency_member(
            agency_id=agency_id,
            email=email,
            role="manager",
        )
        
        assert result is not None
        assert result["email"] == email
        assert result["role"] == "manager"
        assert result["status"] == "pending"
        assert "member_id" in result
        assert result["invited_at"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_agency_members(self, test_agency):
        """Test getting all members of an agency."""
        agency_id = test_agency["agency_id"]
        
        # Insert test members
        await repo.insert_agency_member(agency_id, f"m1-{uuid.uuid4().hex[:8]}@test.com", "admin")
        await repo.insert_agency_member(agency_id, f"m2-{uuid.uuid4().hex[:8]}@test.com", "manager")
        
        members = await repo.get_agency_members(agency_id)
        
        assert len(members) >= 2
        assert all("member_id" in m for m in members)
        assert all("email" in m for m in members)
        assert all("role" in m for m in members)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_agency_used_seats(self, test_agency):
        """Test counting used seats in agency."""
        agency_id = test_agency["agency_id"]
        
        # Initially should be 0
        initial_seats = await repo.get_agency_used_seats(agency_id)
        
        # Add members
        await repo.insert_agency_member(agency_id, f"s1-{uuid.uuid4().hex[:8]}@test.com", "admin")
        await repo.insert_agency_member(agency_id, f"s2-{uuid.uuid4().hex[:8]}@test.com", "manager")
        
        new_seats = await repo.get_agency_used_seats(agency_id)
        
        assert new_seats == initial_seats + 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_member_by_id(self, test_agency):
        """Test getting a member by ID."""
        agency_id = test_agency["agency_id"]
        email = f"findme-{uuid.uuid4().hex[:8]}@test.com"
        
        inserted = await repo.insert_agency_member(agency_id, email, "admin")
        member_id = inserted["member_id"]
        
        found = await repo.get_member_by_id(member_id)
        
        assert found is not None
        assert found["member_id"] == member_id
        assert found["email"] == email
        assert found["role"] == "admin"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_member_by_id_not_found(self, db_connection):
        """Test getting a non-existent member."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_member_by_id(999999999)
        assert found is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_member_by_email(self, test_agency):
        """Test getting a member by email."""
        agency_id = test_agency["agency_id"]
        email = f"byemail-{uuid.uuid4().hex[:8]}@test.com"
        
        await repo.insert_agency_member(agency_id, email, "manager")
        
        found = await repo.get_member_by_email(agency_id, email)
        
        assert found is not None
        assert found["email"] == email

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_member_role(self, test_agency):
        """Test updating a member's role."""
        agency_id = test_agency["agency_id"]
        
        inserted = await repo.insert_agency_member(
            agency_id, f"role-{uuid.uuid4().hex[:8]}@test.com", "manager"
        )
        member_id = inserted["member_id"]
        
        result = await repo.update_member_role(member_id, "admin")
        
        assert result is not None
        assert result["role"] == "admin"
        
        # Verify the change persisted
        member = await repo.get_member_by_id(member_id)
        assert member["role"] == "admin"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_member(self, test_agency):
        """Test deleting a member."""
        agency_id = test_agency["agency_id"]
        
        inserted = await repo.insert_agency_member(
            agency_id, f"delete-{uuid.uuid4().hex[:8]}@test.com", "manager"
        )
        member_id = inserted["member_id"]
        
        # Verify exists
        assert await repo.get_member_by_id(member_id) is not None
        
        # Delete
        success = await repo.delete_member(member_id)
        assert success is True
        
        # Verify deleted
        assert await repo.get_member_by_id(member_id) is None


class TestInviteRepo:
    """Tests for invite repository functions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_and_get_invite(self, test_agency):
        """Test creating and retrieving an invite."""
        agency_id = test_agency["agency_id"]
        
        # Create member first
        member = await repo.insert_agency_member(
            agency_id, f"inv-{uuid.uuid4().hex[:8]}@test.com", "manager"
        )
        member_id = member["member_id"]
        
        # Create invite
        invite = await repo.create_invite(member_id=member_id)
        
        assert invite is not None
        assert "token" in invite
        assert "expires_at" in invite
        
        # Retrieve by token
        found = await repo.get_invite_by_token(invite["token"])
        
        assert found is not None
        assert found["member_id"] == member_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_invite_invalid_token(self, db_connection):
        """Test getting invite with invalid token."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_invite_by_token("invalid-token-12345")
        assert found is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_invites_by_member(self, test_agency):
        """Test deleting all invites for a member."""
        agency_id = test_agency["agency_id"]
        
        member = await repo.insert_agency_member(
            agency_id, f"delinv-{uuid.uuid4().hex[:8]}@test.com", "manager"
        )
        member_id = member["member_id"]
        
        # Create multiple invites
        inv1 = await repo.create_invite(member_id=member_id)
        inv2 = await repo.create_invite(member_id=member_id)
        
        # Delete all
        success = await repo.delete_invites_by_member(member_id)
        assert success is True
        
        # Verify both deleted
        assert await repo.get_invite_by_token(inv1["token"]) is None
        assert await repo.get_invite_by_token(inv2["token"]) is None


class TestClientRepo:
    """Tests for client repository functions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_insert_client(self, test_agency):
        """Test creating a new client."""
        agency_id = test_agency["agency_id"]
        
        result = await repo.insert_client(
            agency_id=agency_id,
            name="Test Client Corp",
            admin_email=f"admin-{uuid.uuid4().hex[:8]}@client.com",
            plan="pro",
        )
        
        assert result is not None
        assert result["name"] == "Test Client Corp"
        assert result["plan"] == "pro"
        assert result["status"] == "onboarding"
        assert result["linkedin_connected"] is False
        assert "client_id" in result

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_agency_clients(self, test_agency):
        """Test getting all clients for an agency."""
        agency_id = test_agency["agency_id"]
        
        # Insert test clients
        await repo.insert_client(
            agency_id, "Client A", f"a-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        await repo.insert_client(
            agency_id, "Client B", f"b-{uuid.uuid4().hex[:8]}@test.com", "pro"
        )
        
        clients = await repo.get_agency_clients(agency_id)
        
        assert len(clients) >= 2
        assert all("client_id" in c for c in clients)
        assert all("name" in c for c in clients)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_agency_clients_filtered_by_search(self, test_agency):
        """Test filtering clients by search term."""
        agency_id = test_agency["agency_id"]
        unique_name = f"UniqueCompany{uuid.uuid4().hex[:8]}"
        
        await repo.insert_client(
            agency_id, unique_name, f"unique-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        await repo.insert_client(
            agency_id, "Other Corp", f"other-{uuid.uuid4().hex[:8]}@test.com", "pro"
        )
        
        # Search for unique name
        clients = await repo.get_agency_clients(agency_id, search=unique_name[:10])
        
        assert len(clients) >= 1
        assert any(unique_name in c["name"] for c in clients)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_client_by_id(self, test_agency):
        """Test getting a client by ID."""
        agency_id = test_agency["agency_id"]
        
        inserted = await repo.insert_client(
            agency_id, "Find Me Corp", f"findme-{uuid.uuid4().hex[:8]}@test.com", "enterprise"
        )
        client_id = inserted["client_id"]
        
        found = await repo.get_client_by_id(client_id)
        
        assert found is not None
        assert found["client_id"] == client_id
        assert found["name"] == "Find Me Corp"
        assert found["plan"] == "enterprise"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_client_by_id_not_found(self, db_connection):
        """Test getting a non-existent client."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_client_by_id(999999999)
        assert found is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_client(self, test_agency):
        """Test updating client details."""
        agency_id = test_agency["agency_id"]
        
        inserted = await repo.insert_client(
            agency_id, "Old Name", f"update-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        client_id = inserted["client_id"]
        
        updated = await repo.update_client(client_id, name="New Name", plan="pro")
        
        assert updated is not None
        assert updated["name"] == "New Name"
        assert updated["plan"] == "pro"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_client(self, test_agency):
        """Test deleting a client."""
        agency_id = test_agency["agency_id"]
        
        inserted = await repo.insert_client(
            agency_id, "Delete Me", f"delete-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        client_id = inserted["client_id"]
        
        # Verify exists
        assert await repo.get_client_by_id(client_id) is not None
        
        # Delete
        success = await repo.delete_client(client_id)
        assert success is True
        
        # Verify deleted
        assert await repo.get_client_by_id(client_id) is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_count_agency_clients(self, test_agency):
        """Test counting clients."""
        agency_id = test_agency["agency_id"]
        
        initial_count = await repo.count_agency_clients(agency_id)
        
        await repo.insert_client(
            agency_id, "Count Test", f"count-{uuid.uuid4().hex[:8]}@test.com", "starter"
        )
        
        new_count = await repo.count_agency_clients(agency_id)
        
        assert new_count == initial_count + 1


class TestImpersonationRepo:
    """Tests for impersonation token repository functions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_impersonation_token(self, test_agency):
        """Test creating an impersonation token."""
        agency_id = test_agency["agency_id"]
        
        # Create member and client
        member = await repo.insert_agency_member(
            agency_id, f"imp-member-{uuid.uuid4().hex[:8]}@test.com", "admin"
        )
        client = await repo.insert_client(
            agency_id, "Imp Client", f"imp-{uuid.uuid4().hex[:8]}@test.com", "pro"
        )
        
        token_data = await repo.create_impersonation_token(
            client_id=client["client_id"],
            member_id=member["member_id"],
        )
        
        assert token_data is not None
        assert "token" in token_data
        assert "expires_at" in token_data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_impersonation_token(self, test_agency):
        """Test validating an impersonation token."""
        agency_id = test_agency["agency_id"]
        
        member = await repo.insert_agency_member(
            agency_id, f"imp2-{uuid.uuid4().hex[:8]}@test.com", "admin"
        )
        client = await repo.insert_client(
            agency_id, "Imp Client 2", f"imp2-{uuid.uuid4().hex[:8]}@test.com", "pro"
        )
        
        created = await repo.create_impersonation_token(
            client_id=client["client_id"],
            member_id=member["member_id"],
        )
        
        found = await repo.get_impersonation_token(created["token"])
        
        assert found is not None
        assert found["client_id"] == client["client_id"]
        assert found["agency_member_id"] == member["member_id"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_impersonation_token_invalid(self, db_connection):
        """Test validating an invalid token."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_impersonation_token("invalid-impersonation-token")
        assert found is None

