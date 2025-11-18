import asyncpg
from air1.config import settings
from typing import Optional

pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password,
            min_size=1,
            max_size=20,
            ssl="disable",
        )
    return pool


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


class Database:
    async def get_pool(self) -> asyncpg.Pool:
        global pool
        if pool is None:
            pool = await init_pool()
        return pool

    async def fetch(self, query, *args):
        pool = await self.get_pool()
        return await pool.fetch(query, *args)

    async def fetchrow(self, query, *args):
        pool = await self.get_pool()
        return await pool.fetchrow(query, *args)

    async def execute(self, query, *args):
        pool = await self.get_pool()
        return await pool.execute(query, *args)


db = Database()
