import asyncpg
from air1.config import settings

pool: asyncpg.Pool = None


async def init_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password,
            min_size=10,
            max_size=10,
        )
    return pool


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


class Database:

    @property
    def pool(self):
        if pool is None:
            raise RuntimeError("Database not initialized. Call init_pool() first.")
        return pool

    async def fetch(self, query, *args):
        if pool is None:
            await init_pool()
        return await pool.fetch(query, *args)

    async def fetchrow(self, query, *args):
        if pool is None:
            await init_pool()
        return await pool.fetchrow(query, *args)

    async def execute(self, query, *args):
        if pool is None:
            await init_pool()
        return await pool.execute(query, *args)


db = Database()
