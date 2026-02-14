"""Unit tests for leadgen API routes."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


from air1.api.auth import AuthUser


@pytest.fixture
def mock_user():
    return AuthUser(user_id="user_test123", email="test@example.com")


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.create_search = AsyncMock(return_value=1)
    svc.run_search = AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# list_software
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListSoftware:
    @pytest.mark.asyncio
    async def test_returns_builtin_patterns(self, mock_user):
        from air1.api.routes.leadgen import list_software

        with patch("air1.api.routes.leadgen.get_current_user", return_value=mock_user):
            result = await list_software(_current_user=mock_user)

        assert len(result) > 0
        slugs = [r.slug for r in result]
        assert "cloudbeds" in slugs
        assert "shopify" in slugs


# ---------------------------------------------------------------------------
# create_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateSearch:
    @pytest.mark.asyncio
    async def test_creates_search(self, mock_user, mock_service):
        from air1.api.routes.leadgen import create_search
        from air1.api.models.leadgen import CreateSearchRequest
        from air1.services.leadgen.models import SearchStats

        mock_service.run_search = AsyncMock(
            return_value=SearchStats(
                businesses_found=10,
                businesses_with_website=8,
                detected_count=3,
            )
        )

        request = CreateSearchRequest(
            softwareSlug="cloudbeds",
            centerLat=25.76,
            centerLng=-80.19,
            radiusKm=10.0,
            businessType="hotel",
        )

        with patch("air1.api.routes.leadgen._get_service", return_value=mock_service):
            result = await create_search(request=request, current_user=mock_user)

        assert result.search_id == 1
        assert result.status == "completed"
        assert result.stats.businesses_found == 10
        assert result.stats.detected_count == 3
        mock_service.create_search.assert_awaited_once()
        mock_service.run_search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_slug_returns_400(self, mock_user, mock_service):
        from air1.api.routes.leadgen import create_search
        from air1.api.models.leadgen import CreateSearchRequest
        from fastapi import HTTPException

        mock_service.create_search = AsyncMock(
            side_effect=ValueError("Unknown software 'xyz'")
        )

        request = CreateSearchRequest(
            softwareSlug="xyz",
            centerLat=25.0,
            centerLng=-80.0,
        )

        with patch("air1.api.routes.leadgen._get_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc_info:
                await create_search(request=request, current_user=mock_user)

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# get_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSearch:
    @pytest.mark.asyncio
    async def test_returns_search(self, mock_user):
        from air1.api.routes.leadgen import get_search

        mock_search = {
            "software_product_id": 1,
            "user_id": "user_test123",
            "status": "completed",
            "stats": {"businesses_found": 5, "detected_count": 2},
            "created_at": "2026-01-01T00:00:00",
        }
        mock_product = {"name": "Cloudbeds", "slug": "cloudbeds"}

        with patch("air1.services.leadgen.repo.get_lead_search", new_callable=AsyncMock, return_value=mock_search):
            with patch("air1.services.leadgen.repo.get_software_product_by_id", new_callable=AsyncMock, return_value=mock_product):
                result = await get_search(search_id=1, current_user=mock_user)

        assert result.search_id == 1
        assert result.status == "completed"
        assert result.software_name == "Cloudbeds"

    @pytest.mark.asyncio
    async def test_wrong_user_returns_404(self, mock_user):
        from air1.api.routes.leadgen import get_search
        from fastapi import HTTPException

        mock_search = {
            "software_product_id": 1,
            "user_id": "different_user",
            "status": "completed",
        }

        with patch("air1.services.leadgen.repo.get_lead_search", new_callable=AsyncMock, return_value=mock_search):
            with pytest.raises(HTTPException) as exc_info:
                await get_search(search_id=1, current_user=mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, mock_user):
        from air1.api.routes.leadgen import get_search
        from fastapi import HTTPException

        with patch("air1.services.leadgen.repo.get_lead_search", new_callable=AsyncMock, return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_search(search_id=999, current_user=mock_user)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_search_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSearchResults:
    @pytest.mark.asyncio
    async def test_returns_results(self, mock_user):
        from air1.api.routes.leadgen import get_search_results

        mock_search = {"user_id": "user_test123", "status": "completed"}
        mock_leads = [
            {"id": 1, "name": "Hotel A", "website": "https://a.com", "detection_status": "detected", "detected_software": "Cloudbeds"},
            {"id": 2, "name": "Hotel B", "detection_status": "not_detected"},
        ]

        with patch("air1.services.leadgen.repo.get_lead_search", new_callable=AsyncMock, return_value=mock_search):
            with patch("air1.services.leadgen.repo.get_search_results", new_callable=AsyncMock, return_value=mock_leads):
                result = await get_search_results(search_id=1, detected_only=False, current_user=mock_user)

        assert result.total == 2
        assert result.leads[0].name == "Hotel A"
        assert result.leads[0].detected_software == "Cloudbeds"

    @pytest.mark.asyncio
    async def test_detected_only_filter(self, mock_user):
        from air1.api.routes.leadgen import get_search_results

        mock_search = {"user_id": "user_test123", "status": "completed"}
        mock_leads = [
            {"id": 1, "name": "Hotel A", "detection_status": "detected", "detected_software": "Cloudbeds"},
        ]

        with patch("air1.services.leadgen.repo.get_lead_search", new_callable=AsyncMock, return_value=mock_search):
            with patch("air1.services.leadgen.repo.get_detected_leads", new_callable=AsyncMock, return_value=mock_leads):
                result = await get_search_results(search_id=1, detected_only=True, current_user=mock_user)

        assert result.total == 1
