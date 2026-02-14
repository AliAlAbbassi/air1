"""Brandfetch API client for company logo and domain enrichment.

Brandfetch API: https://docs.brandfetch.com/reference/searchbrandfetch
Free tier: 500K requests/month, no credit card required
"""

import httpx
from typing import Optional
from loguru import logger


class BrandfetchClient:
    """Client for Brandfetch Logo API."""

    BASE_URL = "https://api.brandfetch.io/v2"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Brandfetch client.

        Args:
            api_key: Brandfetch API key (optional for public API)
        """
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def search_company(self, company_name: str) -> Optional[dict]:
        """Search for a company by name and return brand data.

        Args:
            company_name: The company name to search for

        Returns:
            Brand data dict with domain, name, logos, etc. or None if not found
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Search endpoint
                response = await client.get(
                    f"{self.BASE_URL}/search/{company_name}",
                    headers=self.headers,
                )
                response.raise_for_status()

                data = response.json()
                if not data:
                    return None

                # Get first result
                results = data if isinstance(data, list) else [data]
                if not results:
                    return None

                brand = results[0]
                return {
                    "domain": brand.get("domain"),
                    "name": brand.get("name"),
                    "description": brand.get("description"),
                    "logos": brand.get("logos", []),
                    "website": f"https://{brand.get('domain')}" if brand.get("domain") else None,
                }

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.debug(f"Company not found: {company_name}")
                    return None
                logger.warning(f"Brandfetch API error for {company_name}: {e}")
                return None
            except Exception as e:
                logger.warning(f"Failed to fetch brand data for {company_name}: {e}")
                return None

    async def get_by_domain(self, domain: str) -> Optional[dict]:
        """Get brand data by domain.

        Args:
            domain: The company domain (e.g., "anthropic.com")

        Returns:
            Brand data dict or None if not found
        """
        # Remove protocol if present
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/brands/{domain}",
                    headers=self.headers,
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "domain": data.get("domain"),
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "logos": data.get("logos", []),
                    "website": f"https://{data.get('domain')}" if data.get("domain") else None,
                }

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.debug(f"Domain not found: {domain}")
                    return None
                logger.warning(f"Brandfetch API error for {domain}: {e}")
                return None
            except Exception as e:
                logger.warning(f"Failed to fetch brand data for {domain}: {e}")
                return None
