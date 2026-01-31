"""Account service module for user and admin management."""

from .service import Service, IService, AdminError, AdminResult

__all__ = ["Service", "IService", "AdminError", "AdminResult"]

