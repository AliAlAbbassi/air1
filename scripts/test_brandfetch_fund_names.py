"""Test Brandfetch with actual fund names from our database."""

import asyncio

from air1.services.enrichment.brandfetch_client import BrandfetchClient


async def main():
    client = BrandfetchClient()

    # Test with actual company names from DB
    test_companies = [
        "Collage Labs Inc.",
        "Evoke Innovation Fund II, LP",
        "Blackstone Capital Opportunities Fund V LP",
        "Nuvion AI Dec 2025 a Series of CGF2021 LLC",
        "SILVER SCREEN FUND, LLC",
        "Deako Note Dec 2025 a Series of CGF2021 LLC",
        "HH NYPA EyeSouth LLC",
    ]

    for name in test_companies:
        print(f"\nSearching for: {name}")
        result = await client.search_company(name)
        if result:
            print(f"  ✓ Found: {result['domain']}")
            print(f"    Website: {result['website']}")
            print(f"    Name: {result['name']}")
        else:
            print(f"  ✗ Not found in Brandfetch")


if __name__ == "__main__":
    asyncio.run(main())
