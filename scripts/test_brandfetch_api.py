"""Test Brandfetch API directly."""

import asyncio

from air1.services.enrichment.brandfetch_client import BrandfetchClient


async def main():
    client = BrandfetchClient()

    # Test with well-known companies
    test_companies = [
        "Anthropic",
        "OpenAI",
        "Google",
        "Supabase",
        "Vercel",
    ]

    for name in test_companies:
        print(f"\nSearching for: {name}")
        result = await client.search_company(name)
        if result:
            print(f"  ✓ Found: {result['domain']}")
            print(f"    Website: {result['website']}")
            print(f"    Name: {result['name']}")
        else:
            print(f"  ✗ Not found")


if __name__ == "__main__":
    asyncio.run(main())
