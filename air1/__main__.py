import asyncio
from air1.cli.commands import app
from air1.db.db import init_pool


def main():
    asyncio.run(init_pool())
    app()


if __name__ == "__main__":
    main()
