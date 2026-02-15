"""Unit tests for SerperMapsSource grid scraper."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from air1.services.leadgen.models import SearchParams
from air1.services.leadgen.sources.serper_maps import (
    GridCell,
    SerperMapsSource,
    SKIP_DOMAINS,
)


# ---------------------------------------------------------------------------
# GridCell tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGridCell:
    def test_center(self):
        cell = GridCell(lat_min=25.0, lat_max=26.0, lng_min=-81.0, lng_max=-80.0)
        assert cell.center_lat == 25.5
        assert cell.center_lng == -80.5

    def test_size_km(self):
        cell = GridCell(lat_min=25.0, lat_max=25.018, lng_min=-80.02, lng_max=-80.0)
        # ~2km cell at lat 25
        assert cell.size_km > 0

    def test_subdivide_creates_four(self):
        cell = GridCell(lat_min=25.0, lat_max=26.0, lng_min=-81.0, lng_max=-80.0)
        subcells = cell.subdivide()
        assert len(subcells) == 4

    def test_subdivide_covers_area(self):
        cell = GridCell(lat_min=25.0, lat_max=26.0, lng_min=-81.0, lng_max=-80.0)
        subcells = cell.subdivide()
        # Bottom-left subcell
        assert subcells[0].lat_min == 25.0
        assert subcells[0].lat_max == 25.5
        assert subcells[0].lng_min == -81.0
        assert subcells[0].lng_max == -80.5
        # Top-right subcell
        assert subcells[3].lat_min == 25.5
        assert subcells[3].lat_max == 26.0
        assert subcells[3].lng_min == -80.5
        assert subcells[3].lng_max == -80.0


# ---------------------------------------------------------------------------
# SerperMapsSource tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSerperMapsSource:
    def test_init(self):
        source = SerperMapsSource(api_key="test-key", cell_size_km=2.0)
        assert source.api_key == "test-key"
        assert source.cell_size_km == 2.0
        assert source.api_calls == 0

    def test_generate_grid(self):
        source = SerperMapsSource(api_key="test-key", cell_size_km=5.0)
        cells = source._generate_grid(25.0, 25.09, -80.1, -80.0)
        assert len(cells) > 0
        # Cells should cover the bounding box
        for cell in cells:
            assert cell.lat_min >= 25.0
            assert cell.lat_max <= 25.09
            assert cell.lng_min >= -80.1
            assert cell.lng_max <= -80.0

    def test_get_zoom(self):
        assert SerperMapsSource._get_zoom(0.5) == 15
        assert SerperMapsSource._get_zoom(2.0) == 14
        assert SerperMapsSource._get_zoom(10.0) == 12
        assert SerperMapsSource._get_zoom(50.0) == 12  # fallback

    def test_parse_address(self):
        city, state = SerperMapsSource._parse_address("123 Main St, Miami, FL 33101")
        assert city == "Miami"
        assert state == "FL"

    def test_parse_address_empty(self):
        city, state = SerperMapsSource._parse_address("")
        assert city is None
        assert state is None

    def test_parse_address_short(self):
        city, state = SerperMapsSource._parse_address("Miami")
        assert city is None
        assert state is None

    def test_process_place_basic(self):
        source = SerperMapsSource(api_key="key")
        bounds = (24.0, 27.0, -82.0, -79.0)
        place = {
            "title": "Test Hotel",
            "website": "https://testhotel.com",
            "placeId": "abc123",
            "latitude": 25.76,
            "longitude": -80.19,
            "address": "100 Main St, Miami, FL 33101",
        }
        biz = source._process_place(place, bounds)
        assert biz is not None
        assert biz.name == "Test Hotel"
        assert biz.website == "https://testhotel.com"
        assert biz.google_place_id == "abc123"

    def test_process_place_dedup_by_place_id(self):
        source = SerperMapsSource(api_key="key")
        bounds = (24.0, 27.0, -82.0, -79.0)
        place = {"title": "Hotel", "placeId": "dup1", "latitude": 25.7, "longitude": -80.1}
        # First call succeeds
        assert source._process_place(place, bounds) is not None
        # Second call with same placeId returns None
        assert source._process_place(place, bounds) is None

    def test_process_place_dedup_by_location(self):
        source = SerperMapsSource(api_key="key")
        bounds = (24.0, 27.0, -82.0, -79.0)
        place1 = {"title": "Hotel A", "latitude": 25.7, "longitude": -80.1}
        place2 = {"title": "Hotel B", "latitude": 25.7, "longitude": -80.1}
        assert source._process_place(place1, bounds) is not None
        assert source._process_place(place2, bounds) is None

    def test_process_place_dedup_by_name(self):
        source = SerperMapsSource(api_key="key")
        bounds = (24.0, 27.0, -82.0, -79.0)
        place1 = {"title": "Unique Hotel"}
        place2 = {"title": "unique hotel"}  # case insensitive
        assert source._process_place(place1, bounds) is not None
        assert source._process_place(place2, bounds) is None

    def test_process_place_skips_junk_domain(self):
        source = SerperMapsSource(api_key="key")
        bounds = (24.0, 27.0, -82.0, -79.0)
        for domain in ["facebook.com", "booking.com", "tripadvisor.com"]:
            source._seen_names.clear()
            place = {"title": f"Hotel {domain}", "website": f"https://{domain}/hotel"}
            assert source._process_place(place, bounds) is None

    def test_process_place_out_of_bounds(self):
        source = SerperMapsSource(api_key="key")
        bounds = (25.0, 26.0, -81.0, -80.0)  # tight bounds
        place = {
            "title": "Far Away Hotel",
            "placeId": "far1",
            "latitude": 30.0,  # way outside
            "longitude": -75.0,
        }
        assert source._process_place(place, bounds) is None

    def test_process_place_no_name(self):
        source = SerperMapsSource(api_key="key")
        bounds = (24.0, 27.0, -82.0, -79.0)
        place = {"title": "", "placeId": "empty1"}
        assert source._process_place(place, bounds) is None

    @pytest.mark.asyncio
    async def test_discover_empty_results(self):
        source = SerperMapsSource(api_key="test-key", cell_size_km=50.0)
        params = SearchParams(center_lat=25.76, center_lng=-80.19, radius_km=1.0)

        with patch("air1.services.leadgen.sources.serper_maps.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"places": []}
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await source.discover(params)

        assert results == []
        assert source.api_calls > 0

    @pytest.mark.asyncio
    async def test_search_serper_out_of_credits(self):
        source = SerperMapsSource(api_key="test-key")

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Insufficient credits"
        mock_client.post = AsyncMock(return_value=mock_resp)

        result = await source._search_serper(mock_client, "hotel", 25.0, -80.0, 14)
        assert result == []
        assert source._out_of_credits is True

    @pytest.mark.asyncio
    async def test_search_serper_error_status(self):
        source = SerperMapsSource(api_key="test-key")

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_client.post = AsyncMock(return_value=mock_resp)

        result = await source._search_serper(mock_client, "hotel", 25.0, -80.0, 14)
        assert result == []
        assert source._out_of_credits is False


@pytest.mark.unit
class TestSkipDomains:
    def test_social_media_in_skip_list(self):
        assert "facebook.com" in SKIP_DOMAINS
        assert "instagram.com" in SKIP_DOMAINS

    def test_aggregators_in_skip_list(self):
        assert "booking.com" in SKIP_DOMAINS
        assert "expedia.com" in SKIP_DOMAINS
        assert "airbnb.com" in SKIP_DOMAINS
