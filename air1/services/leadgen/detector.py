"""Software detector using Playwright browser automation.

Visits business websites and detects what software they use by analyzing:
1. HTML source for known patterns (domains, CSS/JS references)
2. URLs and redirects to known software domains
3. Network requests to known API endpoints

Ported and generalized from sadie-gtm's booking engine detector.
"""

import re
import asyncio
import random
from typing import Optional
from urllib.parse import urlparse

from loguru import logger
from playwright.async_api import async_playwright, Browser
from playwright.async_api import TimeoutError as PWTimeoutError

from air1.services.leadgen.models import DetectionResult

try:
    from playwright_stealth import stealth_async

    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


def _extract_domain(url: str) -> str:
    """Extract domain from URL, stripping www. prefix."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _normalize_url(url: str) -> str:
    """Ensure URL has https:// prefix."""
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


class SoftwareDetector:
    """Detects software on websites using Playwright browser automation."""

    def __init__(self, headless: bool = True, timeout_ms: int = 15000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._browser: Optional[Browser] = None
        self._playwright = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def detect(
        self,
        url: str,
        detection_patterns: dict,
        software_name: str = "",
    ) -> DetectionResult:
        """Detect if a website uses the specified software.

        Args:
            url: Website URL to check.
            detection_patterns: Dict with 'domains', 'url_patterns', 'html_patterns'.
            software_name: Name of the software being detected.

        Returns:
            DetectionResult with detection status and method.
        """
        url = _normalize_url(url)
        if not url:
            return DetectionResult(error="no_url")

        if not self._browser:
            return DetectionResult(error="browser_not_started")

        domains = detection_patterns.get("domains", [])
        html_patterns = detection_patterns.get("html_patterns", [])

        context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        if HAS_STEALTH:
            await stealth_async(page)

        # Capture network requests
        network_domains: dict[str, str] = {}

        def on_request(request):
            try:
                host = _extract_domain(request.url)
                if host and host not in network_domains:
                    network_domains[host] = request.url
            except Exception:
                pass

        page.on("request", on_request)

        try:
            # Stage 1: Load page
            try:
                await page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            except PWTimeoutError:
                try:
                    await page.goto(url, timeout=15000, wait_until="commit")
                except Exception:
                    pass

            await asyncio.sleep(0.5)

            # Stage 2: HTML scan
            try:
                html = await page.evaluate("document.documentElement.outerHTML")
            except Exception:
                html = ""

            if html:
                html_lower = html.lower()

                # Check HTML patterns
                for pattern in html_patterns:
                    if pattern.lower() in html_lower:
                        logger.debug(f"HTML match: '{pattern}' on {url}")
                        booking_url = self._find_booking_url(html, domains)
                        return DetectionResult(
                            detected=True,
                            software_name=software_name,
                            method="html_pattern",
                            confidence=0.9,
                            booking_url=booking_url,
                        )

                # Check for domain references in HTML (src, href, etc.)
                for domain in domains:
                    if domain.lower() in html_lower:
                        logger.debug(f"Domain found in HTML: '{domain}' on {url}")
                        booking_url = self._find_booking_url(html, domains)
                        return DetectionResult(
                            detected=True,
                            software_name=software_name,
                            method="html_domain",
                            confidence=0.85,
                            booking_url=booking_url,
                        )

            # Stage 3: Check network requests
            for host, full_url in network_domains.items():
                for domain in domains:
                    if domain.lower() in host.lower():
                        logger.debug(f"Network match: '{domain}' in {host}")
                        return DetectionResult(
                            detected=True,
                            software_name=software_name,
                            method="network_sniff",
                            confidence=0.8,
                            booking_url=full_url,
                        )

            # Stage 4: Scan iframes
            try:
                frames = page.frames
                for frame in frames:
                    frame_url = frame.url
                    for domain in domains:
                        if domain.lower() in frame_url.lower():
                            logger.debug(f"Iframe match: '{domain}' in {frame_url}")
                            return DetectionResult(
                                detected=True,
                                software_name=software_name,
                                method="iframe",
                                confidence=0.85,
                                booking_url=frame_url,
                            )
            except Exception:
                pass

            # Not detected
            return DetectionResult(detected=False)

        except PWTimeoutError:
            return DetectionResult(error="timeout")
        except Exception as e:
            error_msg = str(e).replace("\n", " ")[:100]
            return DetectionResult(error=f"exception: {error_msg}")
        finally:
            await page.close()
            await context.close()

    @staticmethod
    def _find_booking_url(html: str, domains: list[str]) -> str:
        """Extract a booking/reservation URL from HTML that matches known domains."""
        url_pattern = r'(?:src|href|data-src|action)=["\']?(https?://[^"\'\s>]+)'
        found_urls = re.findall(url_pattern, html, re.IGNORECASE)

        for url in found_urls:
            url_lower = url.lower()
            for domain in domains:
                if domain.lower() in url_lower:
                    return url
        return ""

    async def detect_batch(
        self,
        websites: list[tuple[int, str]],
        detection_patterns: dict,
        software_name: str = "",
        concurrency: int = 5,
    ) -> dict[int, DetectionResult]:
        """Detect software on multiple websites concurrently.

        Args:
            websites: List of (lead_id, url) tuples.
            detection_patterns: Detection patterns for the target software.
            software_name: Name of the software being detected.
            concurrency: Max concurrent browser tabs.

        Returns:
            Dict mapping lead_id to DetectionResult.
        """
        sem = asyncio.Semaphore(concurrency)
        results: dict[int, DetectionResult] = {}

        async def _detect_one(lead_id: int, url: str):
            async with sem:
                result = await self.detect(url, detection_patterns, software_name)
                results[lead_id] = result

        await asyncio.gather(
            *[_detect_one(lid, url) for lid, url in websites],
            return_exceptions=True,
        )

        return results
