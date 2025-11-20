import os
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
aiosql.register_adapter("prisma", PrismaAdapter)

# Load queries
query_dir = os.path.join(os.path.dirname(__file__), "query")

# Load all queries from the directory
# They will be available as methods on the 'queries' object
queries = aiosql.from_path(query_dir, "prisma")