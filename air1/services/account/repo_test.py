"""Integration tests for admin repo functions.

These tests run against the real database (Docker localhost).

Run with:
    pytest air1/services/account/repo_test.py -v -s --use-real-db
"""

import pytest
import uuid

from air1.db.prisma_client import get_prisma
from air1.services.account import repo


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


class TestAgencyMemberRepo:
    """Tests for agency member repository functions."""

    @pytest.mark.asyncio
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
    async def test_get_member_by_id_not_found(self, db_connection):
        """Test getting a non-existent member."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_member_by_id(999999999)
        assert found is None

    @pytest.mark.asyncio
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
    async def test_get_invite_invalid_token(self, db_connection):
        """Test getting invite with invalid token."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_invite_by_token("invalid-token-12345")
        assert found is None


class TestClientRepo:
    """Tests for client repository functions."""

    @pytest.mark.asyncio
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
    async def test_get_client_by_id_not_found(self, db_connection):
        """Test getting a non-existent client."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_client_by_id(999999999)
        assert found is None

    @pytest.mark.asyncio
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


class TestImpersonationRepo:
    """Tests for impersonation token repository functions."""

    @pytest.mark.asyncio
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
    async def test_get_impersonation_token_invalid(self, db_connection):
        """Test validating an invalid token."""
        if not db_connection:
            pytest.skip("Database connection required")
        found = await repo.get_impersonation_token("invalid-impersonation-token")
        assert found is None

