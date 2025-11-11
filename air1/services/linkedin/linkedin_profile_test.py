import pytest
from air1.services.linkedin.linkedin_profile import LinkedinProfile, Lead


@pytest.mark.unit
class TestLinkedinProfile:
    """Unit tests for LinkedinProfile model methods."""

    def test_is_talent_positive(self):
        """Test isTalent method with recruiter keywords."""
        test_cases = [
            ("Senior Recruiter at TechCorp", True),
            ("Talent Acquisition Specialist", True),
            ("Technical Recruitment Lead", True),
            ("SDR Manager", True),
            ("Technical Sourcer", True),
            ("Headhunter - Executive Search", True),
            ("HR Business Partner", True),
            ("Placing candidates since 2010", True),
            ("Growth Operations Manager", True),
            ("Organization Development Lead", True),
        ]

        for headline, expected in test_cases:
            profile = LinkedinProfile(headline=headline)
            assert profile.isTalent() == expected, f"Failed for headline: {headline}"

    def test_is_talent_negative(self):
        """Test isTalent method without recruiter keywords."""
        test_cases = [
            ("Senior Software Engineer", False),
            ("Product Manager", False),
            ("Data Scientist", False),
            ("CEO and Founder", False),
        ]

        for headline, expected in test_cases:
            profile = LinkedinProfile(headline=headline)
            assert profile.isTalent() == expected, f"Failed for headline: {headline}"

    def test_is_leader_positive(self):
        """Test isLeader method with leadership keywords."""
        test_cases = [
            ("Engineering Manager at Google", True),
            ("Tech Lead - Frontend Team", True),
            ("Team Lead, Backend Services", True),
            ("Founder & CEO", True),
            ("CTO at StartupXYZ", True),
            ("VP of Engineering", True),
            ("Director of Product", True),
            ("Head of Design", True),
            ("Chief Marketing Officer", True),
        ]

        for headline, expected in test_cases:
            profile = LinkedinProfile(headline=headline)
            assert profile.isLeader() == expected, f"Failed for headline: {headline}"

    def test_is_leader_negative(self):
        """Test isLeader method without leadership keywords."""
        test_cases = [
            ("Senior Software Engineer", False),
            ("Product Designer", False),
            ("Data Analyst", False),
            ("Marketing Specialist", False),
        ]

        for headline, expected in test_cases:
            profile = LinkedinProfile(headline=headline)
            assert profile.isLeader() == expected, f"Failed for headline: {headline}"

    def test_is_engineer_positive(self):
        """Test isEngineer method with engineering keywords."""
        test_cases = [
            ("Senior Software Engineer", True),
            ("Frontend Developer", True),
            ("Python Programmer", True),
            ("Backend Engineer", True),
            ("Frontend Specialist", True),
            ("Fullstack Developer", True),
            ("Full-Stack Engineer", True),
            ("SWE at Meta", True),
            ("Machine Learning Engineer", True),
        ]

        for headline, expected in test_cases:
            profile = LinkedinProfile(headline=headline)
            assert profile.isEngineer() == expected, f"Failed for headline: {headline}"

    def test_is_engineer_negative(self):
        """Test isEngineer method without engineering keywords."""
        test_cases = [
            ("Product Manager", False),
            ("UX Designer", False),
            ("Data Analyst", False),
            ("Sales Representative", False),
        ]

        for headline, expected in test_cases:
            profile = LinkedinProfile(headline=headline)
            assert profile.isEngineer() == expected, f"Failed for headline: {headline}"

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        test_cases = [
            ("SENIOR RECRUITER", "isTalent", True),
            ("engineering MANAGER", "isLeader", True),
            ("Software ENGINEER", "isEngineer", True),
            ("SoFtWaRe EnGiNeEr", "isEngineer", True),
        ]

        for headline, method_name, expected in test_cases:
            profile = LinkedinProfile(headline=headline)
            method = getattr(profile, method_name)
            assert method() == expected, f"Failed for headline: {headline}, method: {method_name}"

    def test_overlapping_categories(self):
        """Test profiles that could match multiple categories."""
        # Engineering Manager - both leader and engineer
        profile = LinkedinProfile(headline="Engineering Manager - Full-Stack Developer")
        assert profile.isLeader() is True
        assert profile.isEngineer() is True
        assert profile.isTalent() is False

        # Technical Recruiter - both talent and engineer
        profile = LinkedinProfile(headline="Technical Recruiter - Former Software Engineer")
        assert profile.isTalent() is True
        assert profile.isEngineer() is True
        assert profile.isLeader() is False


@pytest.mark.unit
class TestLead:
    """Unit tests for Lead model."""

    def test_lead_creation_with_all_fields(self):
        """Test creating a Lead with all fields."""
        lead = Lead(
            first_name="John",
            full_name="John Doe",
            email="john.doe@example.com",
            phone_number="+1234567890"
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
            phone_number="123-456-7890"
        )
        assert lead.email == "test@example.com"
        assert lead.first_name == "Test"