import asyncpg
from typing import Optional
from air1.config import settings


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                host=settings.database_host,
                port=settings.database_port,
                database=settings.database_name,
                user=settings.database_user,
                password=settings.database_password,
                min_size=settings.database_pool_min,
                max_size=settings.database_pool_max,
                timeout=settings.database_pool_timeout
            )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)


db = Database()
