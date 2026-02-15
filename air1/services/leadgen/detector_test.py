"""Unit tests for the software detector."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from air1.services.leadgen.detector import (
    SoftwareDetector,
    _extract_domain,
    _normalize_url,
)
from air1.services.leadgen.models import DetectionResult


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractDomain:
    def test_simple_url(self):
        assert _extract_domain("https://example.com/path") == "example.com"

    def test_strips_www(self):
        assert _extract_domain("https://www.example.com") == "example.com"

    def test_empty(self):
        assert _extract_domain("") == ""

    def test_none(self):
        assert _extract_domain(None) == ""

    def test_with_port(self):
        assert _extract_domain("https://example.com:8080/path") == "example.com:8080"

    def test_subdomain(self):
        assert _extract_domain("https://app.mews.com/booking") == "app.mews.com"


@pytest.mark.unit
class TestNormalizeUrl:
    def test_adds_https(self):
        assert _normalize_url("example.com") == "https://example.com"

    def test_keeps_https(self):
        assert _normalize_url("https://example.com") == "https://example.com"

    def test_keeps_http(self):
        assert _normalize_url("http://example.com") == "http://example.com"

    def test_empty(self):
        assert _normalize_url("") == ""

    def test_none(self):
        assert _normalize_url(None) == ""

    def test_strips_whitespace(self):
        assert _normalize_url("  example.com  ") == "https://example.com"


# ---------------------------------------------------------------------------
# SoftwareDetector tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSoftwareDetector:
    def test_init_defaults(self):
        d = SoftwareDetector()
        assert d.headless is True
        assert d.timeout_ms == 15000
        assert d._browser is None

    @pytest.mark.asyncio
    async def test_detect_empty_url(self):
        d = SoftwareDetector()
        result = await d.detect("", {"domains": []}, "Test")
        assert result.detected is False
        assert result.error == "no_url"

    @pytest.mark.asyncio
    async def test_detect_no_browser(self):
        d = SoftwareDetector()
        result = await d.detect("https://example.com", {"domains": []}, "Test")
        assert result.detected is False
        assert result.error == "browser_not_started"

    @pytest.mark.asyncio
    async def test_detect_html_pattern_match(self):
        """Test that HTML pattern matching works."""
        d = SoftwareDetector()

        # Mock browser and page
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(
            return_value='<html><body><script src="https://cdn.shopify.com/s/shopify.js"></script></body></html>'
        )
        mock_page.frames = []
        mock_page.on = MagicMock()
        mock_page.close = AsyncMock()
        mock_page.goto = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        d._browser = mock_browser

        patterns = {
            "domains": ["cdn.shopify.com"],
            "url_patterns": [],
            "html_patterns": ["cdn.shopify.com", "Shopify.theme"],
        }

        with patch("air1.services.leadgen.detector.asyncio.sleep", new_callable=AsyncMock):
            result = await d.detect("https://mystore.com", patterns, "Shopify")

        assert result.detected is True
        assert result.software_name == "Shopify"
        assert result.method == "html_pattern"

    @pytest.mark.asyncio
    async def test_detect_not_found(self):
        """Test that non-matching HTML returns not detected."""
        d = SoftwareDetector()

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(
            return_value="<html><body><h1>Just a plain website</h1></body></html>"
        )
        mock_page.frames = []
        mock_page.on = MagicMock()
        mock_page.close = AsyncMock()
        mock_page.goto = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        d._browser = mock_browser

        patterns = {
            "domains": ["cloudbeds.com"],
            "url_patterns": [],
            "html_patterns": ["cloudbeds.com"],
        }

        with patch("air1.services.leadgen.detector.asyncio.sleep", new_callable=AsyncMock):
            result = await d.detect("https://plainhotel.com", patterns, "Cloudbeds")

        assert result.detected is False
        assert result.error == ""

    @pytest.mark.asyncio
    async def test_detect_domain_in_html(self):
        """Test domain detection in HTML (stage 2 after html_patterns miss)."""
        d = SoftwareDetector()

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(
            return_value='<html><body><iframe src="https://hotels.cloudbeds.com/res"></iframe></body></html>'
        )
        mock_page.frames = []
        mock_page.on = MagicMock()
        mock_page.close = AsyncMock()
        mock_page.goto = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        d._browser = mock_browser

        patterns = {
            "domains": ["cloudbeds.com"],
            "url_patterns": [],
            "html_patterns": ["cb-booking-engine"],  # Won't match
        }

        with patch("air1.services.leadgen.detector.asyncio.sleep", new_callable=AsyncMock):
            result = await d.detect("https://hotelxyz.com", patterns, "Cloudbeds")

        assert result.detected is True
        assert result.method == "html_domain"

    @pytest.mark.asyncio
    async def test_detect_batch(self):
        """Test batch detection runs concurrently."""
        d = SoftwareDetector()
        d._browser = MagicMock()

        results_returned = [
            DetectionResult(detected=True, software_name="Shopify", method="html_pattern"),
            DetectionResult(detected=False),
        ]
        call_count = 0

        async def mock_detect(url, patterns, name):
            nonlocal call_count
            result = results_returned[call_count]
            call_count += 1
            return result

        d.detect = mock_detect

        websites = [(1, "https://store1.com"), (2, "https://store2.com")]
        patterns = {"domains": [], "url_patterns": [], "html_patterns": []}

        results = await d.detect_batch(websites, patterns, "Shopify", concurrency=2)

        assert len(results) == 2
        assert results[1].detected is True
        assert results[2].detected is False


@pytest.mark.unit
class TestFindBookingUrl:
    def test_finds_matching_url(self):
        html = '<a href="https://hotels.cloudbeds.com/reservation/abc">Book</a>'
        url = SoftwareDetector._find_booking_url(html, ["cloudbeds.com"])
        assert "cloudbeds.com" in url

    def test_returns_empty_when_no_match(self):
        html = '<a href="https://example.com">Link</a>'
        url = SoftwareDetector._find_booking_url(html, ["cloudbeds.com"])
        assert url == ""

    def test_finds_src_attribute(self):
        html = '<script src="https://cdn.shopify.com/s/files/1/shop.js"></script>'
        url = SoftwareDetector._find_booking_url(html, ["cdn.shopify.com"])
        assert "cdn.shopify.com" in url
