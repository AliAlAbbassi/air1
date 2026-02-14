"""Serper.dev Google Search API client for finding company websites.

Serper.dev API: https://serper.dev/
Free tier: 2,500 queries
Paid: $50 for 20,000 queries

Setup:
1. Sign up at https://serper.dev/
2. Get API key from dashboard
3. Set SERPER_API_KEY environment variable
"""

import httpx
import re
from typing import Optional
from urllib.parse import urlparse
from loguru import logger


class SerperClient:
    """Client for Serper.dev Google Search API."""

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str):
        """Initialize Serper client.

        Args:
            api_key: Serper.dev API key
        """
        self.api_key = api_key

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
                response = await client.post(
                    self.BASE_URL,
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "q": query,
                        "num": 5,  # Get top 5 results
                    },
                )
                response.raise_for_status()

                data = response.json()
                organic = data.get("organic", [])

                if not organic:
                    return None

                # Try to find the best result
                for item in organic:
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
                    logger.warning("Serper API quota exceeded")
                elif e.response.status_code == 403:
                    logger.warning("Serper API forbidden - check API key")
                else:
                    logger.warning(f"Serper API error for {company_name}: {e}")
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
            # Social media
            r"facebook\.com",
            r"linkedin\.com",
            r"twitter\.com",
            r"x\.com",
            r"instagram\.com",
            r"youtube\.com",
            # News/Media
            r"bloomberg\.com",
            r"forbes\.com",
            r"reuters\.com",
            r"wsj\.com",
            r"nytimes\.com",
            r"techcrunch\.com",
            r"businesswire\.com",
            r"prnewswire\.com",
            r"marketwatch\.com",
            # Startup databases
            r"crunchbase\.com",
            r"pitchbook\.com",
            r"angel\.co",
            r"angellist\.com",
            r"ycombinator\.com",
            # Financial/SEC databases
            r"sec\.gov",
            r"finance\.yahoo\.com",
            r"otcmarkets\.com",
            r"streetinsider\.com",
            r"disclosurequest\.com",
            r"formds\.com",
            r"whalewisdom\.com",
            # Business databases
            r"bizapedia\.com",
            r"trademarkia\.com",
            r"govtribe\.com",
            r"dnb\.com",
            r"manta\.com",
            # Job sites
            r"glassdoor\.com",
            r"indeed\.com",
            # Other
            r"wikipedia\.org",
            r"github\.com",
            r"mapquest\.com",
        ]

        for pattern in exclude_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return False

        return True
