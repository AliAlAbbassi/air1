"""Test Brandfetch with actual startup names from Form D."""

import asyncio

from air1.services.enrichment.brandfetch_client import BrandfetchClient


async def main():
    client = BrandfetchClient()

    # Test with actual startup names from DB
    test_companies = [
        "Fraud Protection Network, Inc.",
        "ClearCut Surgical, Inc.",
        "Collage Labs Inc.",
        "CareFlo, Inc.",
        "Gamify Analytics Inc",
        "Exum Instruments, Inc.",
        "FMG Records, Inc.",
        "Remarket Space Inc.",
    ]

    found = 0
    for name in test_companies:
        print(f"\nSearching for: {name}")
        result = await client.search_company(name)
        if result:
            print(f"  ✓ Found: {result['domain']}")
            print(f"    Website: {result['website']}")
            print(f"    Name: {result['name']}")
            found += 1
        else:
            print(f"  ✗ Not found in Brandfetch")

    print(f"\n\nSuccess rate: {found}/{len(test_companies)} ({100*found/len(test_companies):.0f}%)")


if __name__ == "__main__":
    asyncio.run(main())
