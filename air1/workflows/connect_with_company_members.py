import asyncio

from air1.services.outreach.service import Service


async def connect_with_company_members(
    company_username: str,
    keywords: list[str] | None = None,
    regions: list[str] | None = None,
    pages: int = 1,
    delay_range: tuple[float, float] = (2.0, 5.0),
) -> int:
    """
    Search for employees at a company and send connection requests.

    This is a thin wrapper around the service method.

    Args:
        company_username: LinkedIn company username (e.g., 'revolut')
        keywords: Keywords to filter employees (e.g., ['recruiter', 'talent'])
        regions: LinkedIn geo region IDs to filter by
        pages: Number of search result pages to process
        delay_range: Min/max seconds to wait between requests (to avoid rate limiting)

    Returns:
        int: Number of successful connection requests sent
    """
    async with Service() as service:
        return await service.connect_with_company_members(
            company_username=company_username,
            keywords=keywords,
            regions=regions,
            pages=pages,
            delay_range=delay_range,
        )


if __name__ == "__main__":
    asyncio.run(
        connect_with_company_members(
            company_username="kingston-stanley",
            keywords=["recruiter", "talent"],
            regions=[],
            pages=7,
        )
    )
