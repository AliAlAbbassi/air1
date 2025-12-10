import os
from typing import Any, Dict, List, Optional, Protocol

import aiosql
from aiosql.adapters.asyncpg import AsyncPGAdapter
from loguru import logger
from prisma.errors import PrismaError


class PrismaAdapter(AsyncPGAdapter):
    """
    Adapter to allow aiosql to work with Prisma Client's query_raw method.
    Inherits from AsyncPGAdapter to leverage its postgres parameter formatting ($1, $2, ...).
    """

    def _handle_prisma_error(
        self, query_name: str, sql: str, parameters: Any, e: Exception
    ) -> None:
        """Handle Prisma database errors consistently."""
        logger.error(f"SQL Error in {query_name}: {e}")
        logger.error(f"Error type: {type(e).__name__}")

        if isinstance(e, PrismaError):
            if hasattr(e, "code"):
                logger.error(f"Prisma error code: {e.code}")
            if hasattr(e, "meta") and e.meta:
                logger.error(f"Prisma meta: {e.meta}")
                if isinstance(e.meta, dict):
                    if "cause" in e.meta:
                        logger.error(f"Database error: {e.meta['cause']}")
                    if "message" in e.meta:
                        logger.error(f"Error message: {e.meta['message']}")
                    if "target" in e.meta:
                        logger.error(f"Error target: {e.meta['target']}")

        logger.error(f"SQL: {sql}")
        logger.error(f"Parameters: {parameters}")

    async def select(self, conn, query_name, sql, parameters, record_class=None):
        """Execute a query and return a list of results."""
        parameters = self.maybe_order_params(query_name, parameters)
        logger.debug(f"Executing SQL: {sql} | Params: {parameters}")
        try:
            return await conn.query_raw(sql, *parameters)
        except Exception as e:
            self._handle_prisma_error(query_name, sql, parameters, e)
            raise

    async def select_one(self, conn, query_name, sql, parameters, record_class=None):
        """Execute a query and return the first result, or None."""
        parameters = self.maybe_order_params(query_name, parameters)
        logger.debug(f"Executing SQL (one): {sql} | Params: {parameters}")
        results = await conn.query_raw(sql, *parameters)
        if results:
            return results[0]
        return None

    async def select_value(self, conn, query_name, sql, parameters):
        """Execute a query and return the first value of the first row."""
        parameters = self.maybe_order_params(query_name, parameters)
        logger.debug(f"Executing SQL (value): {sql} | Params: {parameters}")
        results = await conn.query_raw(sql, *parameters)
        if results:
            # Get the first value from the dict (e.g., count)
            return next(iter(results[0].values()))
        return None

    async def insert_update_delete(self, conn, query_name, sql, parameters):
        """Execute a query that returns no result (or we don't care)."""
        parameters = self.maybe_order_params(query_name, parameters)
        logger.debug(f"Executing SQL (write): {sql} | Params: {parameters}")
        try:
            await conn.query_raw(sql, *parameters)
        except Exception as e:
            self._handle_prisma_error(query_name, sql, parameters, e)
            raise

    async def insert_returning(self, conn, query_name, sql, parameters):
        """Execute a query and return the first row (like select_one)."""
        # Prisma's query_raw returns a list of dictionaries.
        # If RETURNING is used, the list will contain the inserted row(s).
        parameters = self.maybe_order_params(query_name, parameters)
        logger.debug(f"Executing SQL (insert+return): {sql} | Params: {parameters}")
        try:
            results = await conn.query_raw(sql, *parameters)
            logger.debug(f"Query result: {results}")
            if results and len(results) > 0:
                return results[0]
            return None
        except Exception as e:
            self._handle_prisma_error(query_name, sql, parameters, e)
            raise


# Register the adapter
aiosql.register_adapter("prisma", PrismaAdapter)  # type: ignore

# Load queries
query_dir = os.path.join(os.path.dirname(__file__), "query")


class OutreachQueries(Protocol):
    # leads.sql
    async def insert_lead(
        self,
        conn: Any,
        *,
        first_name: Optional[str] = None,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def select_all_leads(self, conn: Any) -> List[Dict[str, Any]]: ...

    # linkedin.sql
    async def insert_linkedin_profile(
        self,
        conn: Any,
        *,
        lead_id: int,
        username: str,
        location: Optional[str] = None,
        headline: Optional[str] = None,
        about: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def get_linkedin_profile_by_username(
        self, conn: Any, *, username: str
    ) -> Optional[Dict[str, Any]]: ...

    async def get_company_leads_by_headline(
        self, conn: Any, *, company_username: str, search_term: str, limit: int
    ) -> List[Dict[str, Any]]: ...

    async def get_company_leads(
        self, conn: Any, *, company_username: str
    ) -> List[Dict[str, Any]]: ...

    # linkedin_company_members.sql
    async def insert_linkedin_company_member(
        self,
        conn: Any,
        *,
        linkedin_profile_id: int,
        username: str,
        title: Optional[str] = None,
    ) -> None: ...

    async def get_company_members_by_username(
        self, conn: Any, *, username: str
    ) -> List[Dict[str, Any]]: ...

    async def get_company_member_by_profile_and_username(
        self, conn: Any, *, linkedin_profile_id: int, username: str
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_contact_point(
        self, conn: Any, *, lead_id: int, contact_point_type_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_contact_point_type(
        self, conn: Any, *, contact_point_type: str
    ) -> Optional[Dict[str, Any]]: ...


class OnboardingQueries(Protocol):
    """
    Protocol for onboarding SQL queries.
    Note: aiosql generates functions that accept **kwargs matching SQL :param names.
    """

    async def get_user_by_email(
        self, conn: Any, *, email: str
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_user(
        self, conn: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_user_company(
        self, conn: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_user_product(
        self, conn: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_user_writing_style(
        self, conn: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]: ...


class AccountQueries(Protocol):
    """Protocol for account SQL queries."""

    async def get_account_by_user_id(
        self, conn: Any, *, user_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def update_user_profile(
        self,
        conn: Any,
        *,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> None: ...


# Load queries for the Outreach service
# This object contains methods from all SQL files in the directory
outreach_queries: OutreachQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
onboarding_queries: OnboardingQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
account_queries: AccountQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
