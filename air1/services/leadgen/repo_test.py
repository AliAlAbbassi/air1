"""Unit tests for leadgen repository functions."""

import json

import pytest
from unittest.mock import AsyncMock, patch

from air1.services.leadgen import repo


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_prisma(mock_db):
    with patch("air1.services.leadgen.repo.get_prisma", new_callable=AsyncMock) as m:
        m.return_value = mock_db
        yield mock_db


@pytest.fixture(autouse=True)
def mock_queries():
    with patch("air1.services.leadgen.repo.leadgen_queries") as m:
        yield m


# ---------------------------------------------------------------------------
# get_software_product
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSoftwareProduct:
    @pytest.mark.asyncio
    async def test_returns_product(self, mock_db, mock_queries):
        mock_queries.get_software_product_by_slug = AsyncMock(
            return_value={"id": 1, "name": "Cloudbeds", "slug": "cloudbeds"}
        )
        result = await repo.get_software_product("cloudbeds")
        assert result["id"] == 1
        mock_queries.get_software_product_by_slug.assert_awaited_once_with(
            mock_db, slug="cloudbeds"
        )

    @pytest.mark.asyncio
    async def test_returns_none(self, mock_db, mock_queries):
        mock_queries.get_software_product_by_slug = AsyncMock(return_value=None)
        result = await repo.get_software_product("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# upsert_software_product
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpsertSoftwareProduct:
    @pytest.mark.asyncio
    async def test_upserts(self, mock_db, mock_queries):
        mock_queries.insert_software_product = AsyncMock(
            return_value={"id": 5, "name": "Shopify", "slug": "shopify"}
        )
        result = await repo.upsert_software_product(
            name="Shopify",
            slug="shopify",
            website="https://shopify.com",
            detection_patterns={"domains": ["cdn.shopify.com"]},
        )
        assert result["id"] == 5
        call_kwargs = mock_queries.insert_software_product.call_args[1]
        assert call_kwargs["name"] == "Shopify"
        assert call_kwargs["slug"] == "shopify"
        # detection_patterns should be JSON-serialized
        assert json.loads(call_kwargs["detection_patterns"]) == {"domains": ["cdn.shopify.com"]}


# ---------------------------------------------------------------------------
# create_lead_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateLeadSearch:
    @pytest.mark.asyncio
    async def test_creates_and_returns_id(self, mock_db, mock_queries):
        mock_queries.insert_lead_search = AsyncMock(return_value={"id": 42})
        search_id = await repo.create_lead_search(
            software_product_id=1,
            search_params={"center_lat": 25.0},
            user_id="user_clerk_abc",
        )
        assert search_id == 42
        call_kwargs = mock_queries.insert_lead_search.call_args[1]
        assert call_kwargs["user_id"] == "user_clerk_abc"
        assert call_kwargs["status"] == "pending"

    @pytest.mark.asyncio
    async def test_user_id_none(self, mock_db, mock_queries):
        mock_queries.insert_lead_search = AsyncMock(return_value={"id": 1})
        await repo.create_lead_search(
            software_product_id=1, search_params={}, user_id=None
        )
        call_kwargs = mock_queries.insert_lead_search.call_args[1]
        assert call_kwargs["user_id"] is None


# ---------------------------------------------------------------------------
# update_search_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateSearchStatus:
    @pytest.mark.asyncio
    async def test_updates_with_stats(self, mock_db, mock_queries):
        mock_queries.update_lead_search_status = AsyncMock()
        await repo.update_search_status(1, "completed", {"detected": 5})
        call_kwargs = mock_queries.update_lead_search_status.call_args[1]
        assert call_kwargs["status"] == "completed"
        assert json.loads(call_kwargs["stats"]) == {"detected": 5}

    @pytest.mark.asyncio
    async def test_updates_without_stats(self, mock_db, mock_queries):
        mock_queries.update_lead_search_status = AsyncMock()
        await repo.update_search_status(1, "scraping")
        call_kwargs = mock_queries.update_lead_search_status.call_args[1]
        assert call_kwargs["stats"] == "{}"


# ---------------------------------------------------------------------------
# batch_insert_leads
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchInsertLeads:
    @pytest.mark.asyncio
    async def test_empty_list_returns_zero(self, mock_db):
        result = await repo.batch_insert_leads(1, [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_inserts_leads(self, mock_db):
        mock_db.query_raw = AsyncMock()
        leads = [
            {"name": "Hotel A", "website": "https://a.com", "source": "serper_maps"},
            {"name": "Hotel B"},
        ]
        result = await repo.batch_insert_leads(search_id=1, leads=leads)
        assert result == 2
        mock_db.query_raw.assert_awaited_once()
        # Check SQL contains VALUES for 2 rows
        sql = mock_db.query_raw.call_args[0][0]
        assert "INSERT INTO search_leads" in sql


# ---------------------------------------------------------------------------
# update_lead_detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateLeadDetection:
    @pytest.mark.asyncio
    async def test_updates_detected(self, mock_db, mock_queries):
        mock_queries.update_lead_detection = AsyncMock()
        await repo.update_lead_detection(
            lead_id=1,
            detection_status="detected",
            detected_software="Cloudbeds",
            detection_method="html_pattern",
            detection_details={"confidence": 0.9},
        )
        call_kwargs = mock_queries.update_lead_detection.call_args[1]
        assert call_kwargs["detection_status"] == "detected"
        assert call_kwargs["detected_software"] == "Cloudbeds"
        assert json.loads(call_kwargs["detection_details"]) == {"confidence": 0.9}

    @pytest.mark.asyncio
    async def test_updates_not_detected(self, mock_db, mock_queries):
        mock_queries.update_lead_detection = AsyncMock()
        await repo.update_lead_detection(
            lead_id=1, detection_status="not_detected"
        )
        call_kwargs = mock_queries.update_lead_detection.call_args[1]
        assert call_kwargs["detection_status"] == "not_detected"
        assert call_kwargs["detected_software"] is None


# ---------------------------------------------------------------------------
# get helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetHelpers:
    @pytest.mark.asyncio
    async def test_get_lead_search(self, mock_db, mock_queries):
        mock_queries.get_lead_search = AsyncMock(return_value={"id": 1, "status": "pending"})
        result = await repo.get_lead_search(1)
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_software_product_by_id(self, mock_db, mock_queries):
        mock_queries.get_software_product_by_id = AsyncMock(
            return_value={"id": 1, "name": "Test"}
        )
        result = await repo.get_software_product_by_id(1)
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_pending_leads(self, mock_db, mock_queries):
        mock_queries.get_pending_leads = AsyncMock(
            return_value=[{"id": 1, "website": "https://a.com"}]
        )
        result = await repo.get_pending_leads(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_search_results(self, mock_db, mock_queries):
        mock_queries.get_search_results = AsyncMock(return_value=[])
        result = await repo.get_search_results(1)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_detected_leads(self, mock_db, mock_queries):
        mock_queries.get_detected_leads = AsyncMock(
            return_value=[{"id": 1, "detected_software": "Shopify"}]
        )
        result = await repo.get_detected_leads(1)
        assert len(result) == 1
        assert result[0]["detected_software"] == "Shopify"
