"""Custom exceptions for the outreach service."""


class OutreachError(Exception):
    """Base exception for all outreach-related errors."""


class LinkedInError(OutreachError):
    """Base exception for LinkedIn-related errors."""


class LinkedInAuthenticationError(LinkedInError):
    """Raised when LinkedIn authentication fails (expired/invalid session token)."""


class LinkedInRateLimitError(LinkedInError):
    """Raised when LinkedIn rate limits are exceeded (429 errors)."""


class ProfileScrapingError(LinkedInError):
    """Raised when profile scraping fails due to page structure changes or timeouts."""


class CompanyScrapingError(LinkedInError):
    """Raised when company member scraping fails."""


class DatabaseError(OutreachError):
    """Base exception for database-related errors."""


class LeadInsertionError(DatabaseError):
    """Raised when inserting a lead fails."""


class ProfileInsertionError(DatabaseError):
    """Raised when inserting a LinkedIn profile fails."""


class QueryError(DatabaseError):
    """Raised when a database query fails."""
