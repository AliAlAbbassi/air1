"""Google Custom Search API client for finding company websites.

Google Custom Search API: https://developers.google.com/custom-search/v1/overview
Free tier: 100 queries/day
Paid: $5 per 1000 queries (max 10K/day)

Setup:
1. Create project at https://console.cloud.google.com/
2. Enable Custom Search API
3. Create API key
4. Create Custom Search Engine at https://programmablesearchengine.google.com/
5. Get Search Engine ID (cx parameter)
"""

import httpx
import re
from typing import Optional
from urllib.parse import urlparse
from loguru import logger


class GoogleSearchClient:
    """Client for Google Custom Search API."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, search_engine_id: str):
        """Initialize Google Custom Search client.

        Args:
            api_key: Google API key
            search_engine_id: Custom Search Engine ID (cx parameter)
        """
        self.api_key = api_key
        self.search_engine_id = search_engine_id

    async def search_company(
        self, company_name: str, city: Optional[str] = None, state: Optional[str] = None
    ) -> Optional[str]:
        """Search for a company and extract its website.

        Args:
            company_name: The company name
            city: Optional city for more precise results
            state: Optional state for more precise results

        Returns:
            Website URL or None if not found
        """
        # Build search query with location context
        query = company_name
        if city and state:
            query = f"{company_name} {city} {state}"
        elif state:
            query = f"{company_name} {state}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "key": self.api_key,
                        "cx": self.search_engine_id,
                        "q": query,
                        "num": 3,  # Get top 3 results
                    },
                )
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [])

                if not items:
                    return None

                # Try to find the best result
                for item in items:
                    link = item.get("link", "")
                    if not link:
                        continue

                    # Extract domain
                    domain = self._extract_domain(link)
                    if not domain:
                        continue

                    # Filter out social media, news sites, and databases
                    if self._is_valid_company_domain(domain):
                        return f"https://{domain}"

                return None

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("Google Search API quota exceeded")
                elif e.response.status_code == 403:
                    logger.warning("Google Search API forbidden - check API key")
                else:
                    logger.warning(f"Google Search API error for {company_name}: {e}")
                return None
            except Exception as e:
                logger.warning(f"Failed to search for {company_name}: {e}")
                return None

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract clean domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return None

    def _is_valid_company_domain(self, domain: str) -> bool:
        """Check if domain is likely a company website (not social media, etc)."""
        # Exclude common non-company domains
        exclude_patterns = [
            r"facebook\.com",
            r"linkedin\.com",
            r"twitter\.com",
            r"instagram\.com",
            r"youtube\.com",
            r"crunchbase\.com",
            r"wikipedia\.org",
            r"bloomberg\.com",
            r"forbes\.com",
            r"reuters\.com",
            r"wsj\.com",
            r"nytimes\.com",
            r"sec\.gov",
            r"pitchbook\.com",
            r"angel\.co",
            r"angellist\.com",
            r"ycombinator\.com",
            r"techcrunch\.com",
            r"github\.com",
        ]

        for pattern in exclude_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return False

        return True
