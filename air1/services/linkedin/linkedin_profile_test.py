import pytest
from air1.services.linkedin.linkedin_profile import LinkedinProfile, Lead


@pytest.mark.unit
class TestLinkedinProfile:
    """Unit tests for LinkedinProfile model methods."""



@pytest.mark.unit
class TestLead:
    """Unit tests for Lead model."""

    def test_lead_creation_with_all_fields(self):
        """Test creating a Lead with all fields."""
        lead = Lead(
            first_name="John",
            full_name="John Doe",
            email="john.doe@example.com",
            phone_number="+1234567890",
        )

        assert lead.first_name == "John"
        assert lead.full_name == "John Doe"
        assert lead.email == "john.doe@example.com"
        assert lead.phone_number == "+1234567890"

    def test_lead_creation_with_defaults(self):
        """Test creating a Lead with default values."""
        lead = Lead(email="test@example.com")

        assert lead.first_name == ""
        assert lead.full_name == ""
        assert lead.email == "test@example.com"
        assert lead.phone_number == ""

    def test_lead_validation(self):
        """Test Lead model validation."""
        # Lead with email works fine
        lead = Lead(email="valid@example.com")
        assert lead.email == "valid@example.com"

        # All fields can be set
        lead = Lead(
            email="test@example.com",
            first_name="Test",
            full_name="Test User",
            phone_number="123-456-7890",
        )
        assert lead.email == "test@example.com"
        assert lead.first_name == "Test"
