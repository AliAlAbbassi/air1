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
from loguru import logger

JUNK_DOMAINS = {
    # News/Media
    "bloomberg.com", "forbes.com", "reuters.com", "wsj.com", "nytimes.com",
    "techcrunch.com", "businesswire.com", "prnewswire.com", "marketwatch.com",
    # Financial/SEC databases
    "sec.gov", "otcmarkets.com", "streetinsider.com", "disclosurequest.com",
    "formds.com", "whalewisdom.com",
    # Generic business databases
    "bizapedia.com", "trademarkia.com", "dnb.com", "manta.com", "zoominfo.com",
    "bizprofile.net",
    # Government
    "govtribe.com",
    # Random junk
    "mapquest.com", "issuu.com",
}

SOCIAL_DOMAINS = {
    "linkedin.com", "twitter.com", "x.com", "facebook.com",
    "instagram.com", "youtube.com", "crunchbase.com", "pitchbook.com",
    "github.com",
}


class SerperClient:
    """Client for Serper.dev Google Search API."""

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search_company(
        self, company_name: str, city: Optional[str] = None, state: Optional[str] = None
    ) -> dict:
        """Search for a company and return ALL useful URLs from one query.

        Returns dict: {website, linkedin, twitter, all_results: [{link, title, snippet, domain}]}
        """
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
                    json={"q": query, "num": 10},
                )
                response.raise_for_status()
                data = response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("Serper API quota exceeded")
                else:
                    logger.warning(f"Serper API error for {company_name}: {e}")
                return {"website": None, "linkedin": None, "twitter": None, "all_results": []}
            except Exception as e:
                logger.warning(f"Failed to search for {company_name}: {e}")
                return {"website": None, "linkedin": None, "twitter": None, "all_results": []}

        organic = data.get("organic", [])
        website = None
        linkedin = None
        twitter = None
        all_results = []

        for item in organic:
            link = item.get("link", "")
            if not link:
                continue

            domain = self._extract_domain(link)
            if not domain or self._is_junk(domain):
                continue

            all_results.append({
                "link": link,
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "domain": domain,
            })

            # Extract LinkedIn company page
            if "linkedin.com/company/" in link and not linkedin:
                linkedin = link

            # Extract Twitter/X
            elif re.search(r"(twitter\.com|x\.com)/\w+", link) and not twitter:
                twitter = link

            # Extract primary website (first non-social, non-junk result)
            elif not website and domain not in SOCIAL_DOMAINS:
                website = link

        return {
            "website": website,
            "linkedin": linkedin,
            "twitter": twitter,
            "all_results": all_results,
        }

    @staticmethod
    def _extract_domain(url: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            if domain.startswith("www."):
                domain = domain[4:]
            return domain.lower()
        except Exception:
            return None

    @staticmethod
    def _is_junk(domain: str) -> bool:
        # Check exact match and subdomains (e.g. finance.yahoo.com)
        for junk in JUNK_DOMAINS:
            if domain == junk or domain.endswith("." + junk):
                return True
        return False
