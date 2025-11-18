from prisma import Prisma
from air1.config import settings
import os

prisma = Prisma()

async def connect_db():
    """Connect to the database using Prisma"""
    if not prisma.is_connected():
        os.environ['DATABASE_URL'] = settings.database_url
        await prisma.connect()

async def disconnect_db():
    """Disconnect from the database"""
    if prisma.is_connected():
        await prisma.disconnect()

async def get_prisma() -> Prisma:
    """Get a connected Prisma client instance"""
    await connect_db()
    return prisma