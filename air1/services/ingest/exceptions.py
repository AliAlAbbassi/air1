"""Custom exceptions for the SEC ingest service."""


class IngestError(Exception):
    """Base exception for all ingest-related errors."""


class SECAPIError(IngestError):
    """Raised when a SEC EDGAR API call fails."""


class SECNotFoundError(SECAPIError):
    """Raised when a SEC resource is not found."""


class FormDParsingError(IngestError):
    """Raised when Form D parsing fails."""


class CompanyInsertionError(IngestError):
    """Raised when inserting a SEC company fails unexpectedly."""


class FilingInsertionError(IngestError):
    """Raised when inserting a filing fails unexpectedly."""


class QueryError(IngestError):
    """Raised when a database query fails unexpectedly."""
