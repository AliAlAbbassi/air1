"""Custom exceptions for the outreach service."""


class OutreachError(Exception):
    """Base exception for all outreach-related errors."""

    pass


class LinkedInError(OutreachError):
    """Base exception for LinkedIn-related errors."""

    pass


class LinkedInAuthenticationError(LinkedInError):
    """Raised when LinkedIn authentication fails."""

    pass


class ProfileNotFoundError(LinkedInError):
    """Raised when a LinkedIn profile cannot be found."""

    pass


class ProfileScrapingError(LinkedInError):
    """Raised when profile scraping fails due to page structure changes or timeouts."""

    pass


class CompanyScrapingError(LinkedInError):
    """Raised when company member scraping fails."""

    pass


class NavigationError(LinkedInError):
    """Raised when navigation to a LinkedIn page fails."""

    pass


class DatabaseError(OutreachError):
    """Base exception for database-related errors."""

    pass


class LeadInsertionError(DatabaseError):
    """Raised when inserting a lead fails."""

    pass


class ProfileInsertionError(DatabaseError):
    """Raised when inserting a LinkedIn profile fails."""

    pass


class QueryError(DatabaseError):
    """Raised when a database query fails."""

    pass
