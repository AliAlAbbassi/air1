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

    async def has_linkedin_connection_by_username(
        self, conn: Any, *, username: str
    ) -> Optional[Dict[str, Any]]: ...

    # company.sql
    async def insert_company(
        self,
        conn: Any,
        *,
        name: str,
        linkedin_username: Optional[str] = None,
        source: Optional[str] = None,
        job_geo_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def get_company_by_name(
        self, conn: Any, *, name: str
    ) -> Optional[Dict[str, Any]]: ...

    async def get_companies_by_source(
        self, conn: Any, *, source: str
    ) -> List[Dict[str, Any]]: ...

    async def upsert_company_outreach(
        self,
        conn: Any,
        *,
        company_id: int,
        status: str,
        employees_contacted: int = 0,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def get_companies_with_outreach_status(
        self, conn: Any, *, source: Optional[str] = None
    ) -> List[Dict[str, Any]]: ...

    async def increment_employees_contacted(
        self, conn: Any, *, company_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def update_outreach_status(
        self, conn: Any, *, company_id: int, status: str
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


class AdminQueries(Protocol):
    """Protocol for admin API SQL queries."""

    # Agency & Member queries
    async def get_agency_by_member_user_id(
        self, conn: Any, *, user_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def get_agency_members(
        self, conn: Any, *, agency_id: int
    ) -> List[Dict[str, Any]]: ...

    async def get_agency_used_seats(
        self, conn: Any, *, agency_id: int
    ) -> Optional[int]: ...

    async def get_member_by_id(
        self, conn: Any, *, member_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def get_member_by_email(
        self, conn: Any, *, agency_id: int, email: str
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_agency_member(
        self, conn: Any, *, agency_id: int, email: str, role: str
    ) -> Optional[Dict[str, Any]]: ...

    async def update_member_role(
        self, conn: Any, *, member_id: int, role: str
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_member(
        self, conn: Any, *, member_id: int
    ) -> None: ...

    async def update_member_joined(
        self, conn: Any, *, member_id: int, user_id: int, name: str
    ) -> None: ...

    # Invite queries
    async def create_invite(
        self, conn: Any, *, member_id: Optional[int], client_id: Optional[int],
        token: str, expires_at: Any
    ) -> Optional[Dict[str, Any]]: ...

    async def get_invite_by_token(
        self, conn: Any, *, token: str
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_invite(
        self, conn: Any, *, invite_id: int
    ) -> None: ...

    async def delete_invites_by_member(
        self, conn: Any, *, member_id: int
    ) -> None: ...

    # Client queries
    async def get_agency_clients(
        self, conn: Any, *, agency_id: int
    ) -> List[Dict[str, Any]]: ...

    async def get_agency_clients_filtered(
        self, conn: Any, *, agency_id: int, status: Optional[str], search: Optional[str]
    ) -> List[Dict[str, Any]]: ...

    async def count_agency_clients(
        self, conn: Any, *, agency_id: int, status: Optional[str], search: Optional[str]
    ) -> Optional[int]: ...

    async def get_client_by_id(
        self, conn: Any, *, client_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_client(
        self, conn: Any, *, agency_id: int, name: str, admin_email: str, plan: str
    ) -> Optional[Dict[str, Any]]: ...

    async def update_client(
        self, conn: Any, *, client_id: int, name: Optional[str], plan: Optional[str]
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_client(
        self, conn: Any, *, client_id: int
    ) -> None: ...

    # Client team queries
    async def get_client_team(
        self, conn: Any, *, client_id: int
    ) -> List[Dict[str, Any]]: ...

    # Impersonation queries
    async def create_impersonation_token(
        self, conn: Any, *, client_id: int, member_id: int, token: str, expires_at: Any
    ) -> Optional[Dict[str, Any]]: ...

    async def get_impersonation_token(
        self, conn: Any, *, token: str
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_impersonation_token(
        self, conn: Any, *, token_id: int
    ) -> None: ...


class LeadGenQueries(Protocol):
    """Protocol for leadgen SQL queries."""

    async def get_software_product_by_slug(
        self, conn: Any, *, slug: str
    ) -> Optional[Dict[str, Any]]: ...

    async def get_software_product_by_id(
        self, conn: Any, *, product_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_software_product(
        self, conn: Any, *, name: str, slug: str, website: Optional[str],
        detection_patterns: str
    ) -> Optional[Dict[str, Any]]: ...

    async def insert_lead_search(
        self, conn: Any, *, user_id: Optional[str], software_product_id: int,
        search_params: str, status: str
    ) -> Optional[Dict[str, Any]]: ...

    async def update_lead_search_status(
        self, conn: Any, *, search_id: int, status: str, stats: str
    ) -> None: ...

    async def get_lead_search(
        self, conn: Any, *, search_id: int
    ) -> Optional[Dict[str, Any]]: ...

    async def get_pending_leads(
        self, conn: Any, *, search_id: int
    ) -> List[Dict[str, Any]]: ...

    async def update_lead_detection(
        self, conn: Any, *, lead_id: int, detection_status: str,
        detected_software: Optional[str], detection_method: Optional[str],
        detection_details: str
    ) -> None: ...

    async def get_search_results(
        self, conn: Any, *, search_id: int
    ) -> List[Dict[str, Any]]: ...

    async def get_detected_leads(
        self, conn: Any, *, search_id: int
    ) -> List[Dict[str, Any]]: ...

    async def count_search_leads(
        self, conn: Any, *, search_id: int
    ) -> Optional[int]: ...

    async def count_detected_leads(
        self, conn: Any, *, search_id: int
    ) -> Optional[int]: ...


class EnrichmentQueries(Protocol):
    """Protocol for enrichment SQL queries."""

    async def get_software_companies_without_websites(
        self, conn: Any, *, limit: int
    ) -> List[Dict[str, Any]]: ...


class IngestQueries(Protocol):
    """Protocol for SEC ingest SQL queries."""

    async def upsert_sec_company(
        self,
        conn: Any,
        *,
        cik: str,
        name: str,
        ticker: Optional[str] = None,
        exchange: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def enrich_sec_company(
        self,
        conn: Any,
        *,
        cik: str,
        sic: Optional[str] = None,
        sic_description: Optional[str] = None,
        state_of_incorp: Optional[str] = None,
        fiscal_year_end: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state_or_country: Optional[str] = None,
        zip_code: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
    ) -> None: ...

    async def get_sec_companies_not_enriched(
        self, conn: Any, *, limit: int
    ) -> List[Dict[str, Any]]: ...

    async def count_sec_companies(self, conn: Any) -> Optional[int]: ...

    async def count_sec_companies_not_enriched(
        self, conn: Any
    ) -> Optional[int]: ...

    async def upsert_sec_company_from_issuer(
        self,
        conn: Any,
        *,
        cik: str,
        name: str,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state_or_country: Optional[str] = None,
        zip_code: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def upsert_sec_filing(
        self,
        conn: Any,
        *,
        accession_number: str,
        cik: str,
        form_type: str,
        filing_date: Any,
        company_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def get_form_d_filings_not_parsed(
        self, conn: Any, *, limit: int
    ) -> List[Dict[str, Any]]: ...

    async def link_orphaned_filings(self, conn: Any) -> None: ...

    async def upsert_sec_form_d(
        self, conn: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_officers_by_form_d(
        self, conn: Any, *, sec_form_d_id: int
    ) -> None: ...

    async def insert_sec_officer(
        self, conn: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]: ...

    async def get_recent_form_d_with_officers(
        self, conn: Any, *, since_date: Any, limit: int
    ) -> List[Dict[str, Any]]: ...


# Load queries for the Outreach service
# This object contains methods from all SQL files in the directory
outreach_queries: OutreachQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
onboarding_queries: OnboardingQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
account_queries: AccountQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
admin_queries: AdminQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
ingest_queries: IngestQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
enrichment_queries: EnrichmentQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
leadgen_queries: LeadGenQueries = aiosql.from_path(query_dir, "prisma")  # type: ignore
