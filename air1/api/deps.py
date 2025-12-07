from typing import AsyncGenerator
from prisma import Prisma

# Global database instance
_db: Prisma | None = None


async def get_db() -> AsyncGenerator[Prisma, None]:
    """Get database connection."""
    global _db
    if _db is None:
        _db = Prisma()
        await _db.connect()
    yield _db


async def close_db():
    """Close database connection."""
    global _db
    if _db is not None:
        await _db.disconnect()
        _db = None
