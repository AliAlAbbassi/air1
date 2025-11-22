import os
from typing import Any, Dict, List, Optional, Protocol

import aiosql
from aiosql.adapters.asyncpg import AsyncPGAdapter
from loguru import logger


class PrismaAdapter(AsyncPGAdapter):
    """
    Adapter to allow aiosql to work with Prisma Client's query_raw method.
    Inherits from AsyncPGAdapter to leverage its postgres parameter formatting ($1, $2, ...).
    """

    async def select(self, conn, query_name, sql, parameters, record_class=None):
        """Execute a query and return a list of results."""
        parameters = self.maybe_order_params(query_name, parameters)
        logger.debug(f"Executing SQL: {sql} | Params: {parameters}")
        return await conn.query_raw(sql, *parameters)

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
        await conn.query_raw(sql, *parameters)

    async def insert_returning(self, conn, query_name, sql, parameters):
        """Execute a query and return the first row (like select_one)."""
        # Prisma's query_raw returns a list of dictionaries.
        # If RETURNING is used, the list will contain the inserted row(s).
        parameters = self.maybe_order_params(query_name, parameters)
        logger.debug(f"Executing SQL (insert+return): {sql} | Params: {parameters}")
        results = await conn.query_raw(sql, *parameters)
        if results and len(results) > 0:
            return results[0]
        return None


# Register the adapter
aiosql.register_adapter("prisma", PrismaAdapter())  # type: ignore

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
        self, conn: Any, *, company_username: str, search_term: str
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


# Load queries for the Outreach service
# This object contains methods from all SQL files in the directory
outreach_queries: OutreachQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
