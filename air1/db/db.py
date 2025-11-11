import asyncpg
from air1.config import settings


# Simple connection pool - asyncpg handles everything
pool = None


async def get_pool():
    """Get or create the connection pool"""
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password
        )
    return pool


class Database:
    """Simple wrapper to maintain compatibility"""
    @property
    def pool(self):
        return pool


db = Database()
