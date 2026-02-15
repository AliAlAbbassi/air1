"""Unit tests for leadgen service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from air1.services.leadgen.models import (
    DetectionResult,
    DiscoveredBusiness,
    SearchParams,
)
from air1.services.leadgen.service import Service


@pytest.fixture
def service():
    return Service(serper_api_key="test-key")


# ---------------------------------------------------------------------------
# create_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateSearch:
    @pytest.mark.asyncio
    async def test_creates_search_with_existing_product(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_software_product = AsyncMock(
                return_value={"id": 1, "name": "Cloudbeds", "slug": "cloudbeds"}
            )
            mock_repo.create_lead_search = AsyncMock(return_value=42)

            search_id = await service.create_search(
                software_slug="cloudbeds",
                params=SearchParams(center_lat=25.0, center_lng=-80.0),
                user_id="user_clerk123",
            )

        assert search_id == 42
        mock_repo.create_lead_search.assert_awaited_once()
        call_kwargs = mock_repo.create_lead_search.call_args[1]
        assert call_kwargs["software_product_id"] == 1
        assert call_kwargs["user_id"] == "user_clerk123"

    @pytest.mark.asyncio
    async def test_creates_search_with_builtin_pattern(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_software_product = AsyncMock(return_value=None)
            mock_repo.upsert_software_product = AsyncMock(
                return_value={"id": 5, "name": "Shopify", "slug": "shopify"}
            )
            mock_repo.create_lead_search = AsyncMock(return_value=99)

            search_id = await service.create_search(
                software_slug="shopify",
                params=SearchParams(center_lat=40.7, center_lng=-74.0),
            )

        assert search_id == 99
        mock_repo.upsert_software_product.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_for_unknown_software(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_software_product = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="Unknown software"):
                await service.create_search(
                    software_slug="nonexistent-software-xyz",
                    params=SearchParams(center_lat=25.0, center_lng=-80.0),
                )

    @pytest.mark.asyncio
    async def test_user_id_nullable(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_software_product = AsyncMock(
                return_value={"id": 1, "name": "Test", "slug": "test"}
            )
            mock_repo.create_lead_search = AsyncMock(return_value=1)

            await service.create_search(
                software_slug="test",
                params=SearchParams(center_lat=25.0, center_lng=-80.0),
                user_id=None,
            )

        call_kwargs = mock_repo.create_lead_search.call_args[1]
        assert call_kwargs["user_id"] is None


# ---------------------------------------------------------------------------
# run_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunSearch:
    @pytest.mark.asyncio
    async def test_search_not_found_raises(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="not found"):
                await service.run_search(search_id=999)

    @pytest.mark.asyncio
    async def test_product_not_found_raises(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "search_params": {"center_lat": 25.0, "center_lng": -80.0, "radius_km": 10.0, "business_type": "hotel", "cell_size_km": 2.0},
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="Software product not found"):
                await service.run_search(search_id=1)

    @pytest.mark.asyncio
    async def test_no_businesses_found(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "search_params": {"center_lat": 25.0, "center_lng": -80.0, "radius_km": 10.0, "business_type": "hotel", "cell_size_km": 2.0},
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(
                return_value={
                    "name": "Cloudbeds",
                    "detection_patterns": {"domains": ["cloudbeds.com"], "html_patterns": [], "url_patterns": []},
                }
            )
            mock_repo.update_search_status = AsyncMock()

            with patch("air1.services.leadgen.service.SerperMapsSource") as MockSource:
                mock_source = MagicMock()
                mock_source.discover = AsyncMock(return_value=[])
                mock_source.api_calls = 5
                MockSource.return_value = mock_source

                stats = await service.run_search(search_id=1)

        assert stats.businesses_found == 0
        assert stats.api_calls == 5

    @pytest.mark.asyncio
    async def test_full_pipeline(self, service):
        businesses = [
            DiscoveredBusiness(name="Hotel A", website="https://hotela.com"),
            DiscoveredBusiness(name="Hotel B"),  # No website
        ]

        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "search_params": {"center_lat": 25.0, "center_lng": -80.0, "radius_km": 10.0, "business_type": "hotel", "cell_size_km": 2.0},
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(
                return_value={
                    "name": "Cloudbeds",
                    "detection_patterns": {"domains": ["cloudbeds.com"], "html_patterns": [], "url_patterns": []},
                }
            )
            mock_repo.update_search_status = AsyncMock()
            mock_repo.batch_insert_leads = AsyncMock()
            mock_repo.get_pending_leads = AsyncMock(
                return_value=[{"id": 1, "website": "https://hotela.com"}]
            )
            mock_repo.update_lead_detection = AsyncMock()

            with patch("air1.services.leadgen.service.SerperMapsSource") as MockSource:
                mock_source = MagicMock()
                mock_source.discover = AsyncMock(return_value=businesses)
                mock_source.api_calls = 3
                MockSource.return_value = mock_source

                with patch("air1.services.leadgen.service.SoftwareDetector") as MockDetector:
                    mock_detector = AsyncMock()
                    mock_detector.detect_batch = AsyncMock(
                        return_value={
                            1: DetectionResult(
                                detected=True,
                                software_name="Cloudbeds",
                                method="html_pattern",
                                confidence=0.9,
                            )
                        }
                    )
                    MockDetector.return_value.__aenter__ = AsyncMock(return_value=mock_detector)
                    MockDetector.return_value.__aexit__ = AsyncMock(return_value=False)

                    stats = await service.run_search(search_id=1)

        assert stats.businesses_found == 2
        assert stats.businesses_with_website == 1
        assert stats.detected_count == 1
        assert stats.api_calls == 3
        mock_repo.batch_insert_leads.assert_awaited_once()
        mock_repo.update_lead_detection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_detection_error_counted(self, service):
        businesses = [DiscoveredBusiness(name="Hotel A", website="https://hotela.com")]

        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "search_params": {"center_lat": 25.0, "center_lng": -80.0, "radius_km": 10.0, "business_type": "hotel", "cell_size_km": 2.0},
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(
                return_value={
                    "name": "Cloudbeds",
                    "detection_patterns": {"domains": [], "html_patterns": [], "url_patterns": []},
                }
            )
            mock_repo.update_search_status = AsyncMock()
            mock_repo.batch_insert_leads = AsyncMock()
            mock_repo.get_pending_leads = AsyncMock(
                return_value=[{"id": 1, "website": "https://hotela.com"}]
            )
            mock_repo.update_lead_detection = AsyncMock()

            with patch("air1.services.leadgen.service.SerperMapsSource") as MockSource:
                mock_source = MagicMock()
                mock_source.discover = AsyncMock(return_value=businesses)
                mock_source.api_calls = 1
                MockSource.return_value = mock_source

                with patch("air1.services.leadgen.service.SoftwareDetector") as MockDetector:
                    mock_detector = AsyncMock()
                    mock_detector.detect_batch = AsyncMock(
                        return_value={1: DetectionResult(error="timeout")}
                    )
                    MockDetector.return_value.__aenter__ = AsyncMock(return_value=mock_detector)
                    MockDetector.return_value.__aexit__ = AsyncMock(return_value=False)

                    stats = await service.run_search(search_id=1)

        assert stats.detection_errors == 1
        assert stats.detected_count == 0

    @pytest.mark.asyncio
    async def test_no_pending_leads_skips_detection(self, service):
        businesses = [DiscoveredBusiness(name="Hotel A")]

        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "search_params": {"center_lat": 25.0, "center_lng": -80.0, "radius_km": 10.0, "business_type": "hotel", "cell_size_km": 2.0},
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(
                return_value={
                    "name": "Cloudbeds",
                    "detection_patterns": {"domains": [], "html_patterns": [], "url_patterns": []},
                }
            )
            mock_repo.update_search_status = AsyncMock()
            mock_repo.batch_insert_leads = AsyncMock()
            mock_repo.get_pending_leads = AsyncMock(return_value=[])

            with patch("air1.services.leadgen.service.SerperMapsSource") as MockSource:
                mock_source = MagicMock()
                mock_source.discover = AsyncMock(return_value=businesses)
                mock_source.api_calls = 1
                MockSource.return_value = mock_source

                stats = await service.run_search(search_id=1)

        assert stats.businesses_found == 1
        assert stats.detected_count == 0

    @pytest.mark.asyncio
    async def test_search_params_from_json_string(self, service):
        """Test that search_params stored as JSON string is handled."""
        import json

        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "search_params": json.dumps({
                        "center_lat": 25.0, "center_lng": -80.0,
                        "radius_km": 10.0, "business_type": "hotel", "cell_size_km": 2.0,
                    }),
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(
                return_value={
                    "name": "Test",
                    "detection_patterns": json.dumps({"domains": [], "html_patterns": [], "url_patterns": []}),
                }
            )
            mock_repo.update_search_status = AsyncMock()

            with patch("air1.services.leadgen.service.SerperMapsSource") as MockSource:
                mock_source = MagicMock()
                mock_source.discover = AsyncMock(return_value=[])
                mock_source.api_calls = 0
                MockSource.return_value = mock_source

                stats = await service.run_search(search_id=1)

        assert stats.businesses_found == 0


# ---------------------------------------------------------------------------
# get_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSearch:
    @pytest.mark.asyncio
    async def test_returns_search_for_correct_user(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "user_id": "user_abc",
                    "status": "completed",
                    "stats": {"businesses_found": 10, "detected_count": 3},
                    "created_at": "2026-01-01T00:00:00",
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(
                return_value={"name": "Cloudbeds", "slug": "cloudbeds"}
            )

            result = await service.get_search(search_id=1, user_id="user_abc")

        assert result is not None
        assert result["search_id"] == 1
        assert result["status"] == "completed"
        assert result["software_slug"] == "cloudbeds"
        assert result["software_name"] == "Cloudbeds"
        assert result["stats"]["businesses_found"] == 10

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_user(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "user_id": "user_abc",
                    "status": "completed",
                }
            )

            result = await service.get_search(search_id=1, user_id="different_user")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(return_value=None)

            result = await service.get_search(search_id=999, user_id="user_abc")

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_stats_as_json_string(self, service):
        import json

        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={
                    "software_product_id": 1,
                    "user_id": "user_abc",
                    "status": "completed",
                    "stats": json.dumps({"businesses_found": 5}),
                    "created_at": None,
                }
            )
            mock_repo.get_software_product_by_id = AsyncMock(
                return_value={"name": "Test", "slug": "test"}
            )

            result = await service.get_search(search_id=1, user_id="user_abc")

        assert result["stats"]["businesses_found"] == 5


# ---------------------------------------------------------------------------
# get_search_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSearchResults:
    @pytest.mark.asyncio
    async def test_returns_results_for_correct_user(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={"user_id": "user_abc", "status": "completed"}
            )
            mock_repo.get_search_results = AsyncMock(
                return_value=[
                    {"id": 1, "name": "Hotel A", "detection_status": "detected"},
                    {"id": 2, "name": "Hotel B", "detection_status": "not_detected"},
                ]
            )

            result = await service.get_search_results(search_id=1, user_id="user_abc")

        assert result is not None
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_user(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={"user_id": "user_abc", "status": "completed"}
            )

            result = await service.get_search_results(search_id=1, user_id="different_user")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(return_value=None)

            result = await service.get_search_results(search_id=999, user_id="user_abc")

        assert result is None

    @pytest.mark.asyncio
    async def test_detected_only_filter(self, service):
        with patch("air1.services.leadgen.service.repo") as mock_repo:
            mock_repo.get_lead_search = AsyncMock(
                return_value={"user_id": "user_abc", "status": "completed"}
            )
            mock_repo.get_detected_leads = AsyncMock(
                return_value=[{"id": 1, "name": "Hotel A", "detection_status": "detected"}]
            )

            result = await service.get_search_results(
                search_id=1, user_id="user_abc", detected_only=True
            )

        assert len(result) == 1
        mock_repo.get_detected_leads.assert_awaited_once_with(1)
