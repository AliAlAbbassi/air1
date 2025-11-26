"""Tests for the custom exceptions module."""
import pytest
from air1.services.outreach.exceptions import (
    OutreachError,
    LinkedInError,
    ProfileScrapingError,
    CompanyScrapingError,
    DatabaseError,
    LeadInsertionError,
    ProfileInsertionError,
    QueryError,
)


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test that exception hierarchy is correct."""

    def test_linkedin_errors_inherit_from_outreach_error(self):
        """LinkedIn errors should be catchable as OutreachError."""
        assert issubclass(LinkedInError, OutreachError)
        assert issubclass(ProfileScrapingError, OutreachError)
        assert issubclass(CompanyScrapingError, OutreachError)

    def test_database_errors_inherit_from_outreach_error(self):
        """Database errors should be catchable as OutreachError."""
        assert issubclass(DatabaseError, OutreachError)
        assert issubclass(LeadInsertionError, OutreachError)
        assert issubclass(ProfileInsertionError, OutreachError)
        assert issubclass(QueryError, OutreachError)

    def test_scraping_errors_inherit_from_linkedin_error(self):
        """Scraping errors should be catchable as LinkedInError."""
        assert issubclass(ProfileScrapingError, LinkedInError)
        assert issubclass(CompanyScrapingError, LinkedInError)

    def test_insertion_errors_inherit_from_database_error(self):
        """Insertion errors should be catchable as DatabaseError."""
        assert issubclass(LeadInsertionError, DatabaseError)
        assert issubclass(ProfileInsertionError, DatabaseError)
        assert issubclass(QueryError, DatabaseError)


@pytest.mark.unit
class TestExceptionChaining:
    """Test that exceptions can be properly chained."""

    def test_profile_scraping_error_can_wrap_cause(self):
        """ProfileScrapingError should preserve the original exception."""
        original = ValueError("Original error")
        try:
            raise ProfileScrapingError("Wrapped error") from original
        except ProfileScrapingError as e:
            assert e.__cause__ is original
            assert "Wrapped error" in str(e)

    def test_query_error_can_wrap_cause(self):
        """QueryError should preserve the original exception."""
        original = RuntimeError("DB connection failed")
        try:
            raise QueryError("Query failed") from original
        except QueryError as e:
            assert e.__cause__ is original
