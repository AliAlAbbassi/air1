"""Tools for company finder agent."""

import asyncio

import httpx
from bs4 import BeautifulSoup
from crewai.tools import tool
from loguru import logger

from air1.services.outreach.service import Service


@tool("Web Search")
def web_search_tool(query: str) -> str:
    """
    Search the web for company LinkedIn pages using DuckDuckGo.
    
    Args:
        query: The search query (e.g., 'site:linkedin.com/company/ AI integration software agency')
        
    Returns:
        JSON string containing list of search results with 'title' and 'link'.
    """
    return _perform_ddg_search(query)


@tool("SEC Filing Search")
def sec_filing_search_tool(company_name: str, filing_type: str = "10-K") -> str:
    """
    Search for SEC filings for a company using site:sec.gov.
    
    Args:
        company_name: Name of the company to search for
        filing_type: Type of filing (e.g., "10-K", "S-1", "8-K")
        
    Returns:
        List of search results pointing to SEC filings
    """
    query = f"site:sec.gov {company_name} \"{filing_type}\""
    return _perform_ddg_search(query)


@tool("Crunchbase Search")
def crunchbase_search_tool(company_name: str, keywords: str = "funding") -> str:
    """
    Search for Crunchbase profiles or news using site:crunchbase.com.
    
    Args:
        company_name: Name of the company to search for
        keywords: Additional keywords (e.g., "funding", "acquisition")
        
    Returns:
        List of search results from Crunchbase
    """
    query = f"site:crunchbase.com {company_name} {keywords}"
    return _perform_ddg_search(query)


def _perform_ddg_search(query: str) -> str:
    """Helper to perform DuckDuckGo HTML search."""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, data={"q": query}, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            results = []
            
            # DDG HTML results are usually in .result__body
            for result in soup.select(".result"):
                title_elem = result.select_one(".result__a")
                snippet_elem = result.select_one(".result__snippet")
                
                if title_elem:
                    link = title_elem.get("href")
                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    if link:
                        results.append({
                            "title": title,
                            "link": link,
                            "snippet": snippet
                        })
            
            # Format as simple text list for LLM consumption
            output = [f"Search results for: {query}\n"]
            for i, r in enumerate(results[:10], 1):  # Limit to top 10
                output.append(
                    f"{i}. Title: {r['title']}\n"
                    f"   Link: {r['link']}\n"
                    f"   Snippet: {r['snippet']}\n"
                )
                
            if not results:
                return f"No results found for query: {query}"
                
            return "\n".join(output)
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Error performing search: {str(e)}"


@tool("LinkedIn Company Info")
def linkedin_company_info_tool(linkedin_url: str) -> str:
    """
    Fetch company details from a LinkedIn company URL.
    
    Args:
        linkedin_url: Full LinkedIn company URL (e.g. https://www.linkedin.com/company/openai)
        
    Returns:
        Company information including name, description, industry, and website.
    """
    async def _fetch():
        # Reuse the existing Service logic which handles browser lifecycle
        service = Service()
        return await service.fetch_company_from_linkedin(linkedin_url)

    try:
        # Run async code synchronously for CrewAI tool
        result = asyncio.run(_fetch())
        
        return f"""
        Company Information for: {linkedin_url}
        Name: {result.name}
        Industry: {result.industry}
        Website: {result.website}
        Description: {result.description}
        """
    except Exception as e:
        logger.error(f"Failed to fetch LinkedIn info for {linkedin_url}: {e}")
        return f"Error fetching LinkedIn info: {str(e)}. Ensure LINKEDIN_SID is set and valid."
