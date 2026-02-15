"""Unit tests for leadgen models."""

import pytest

from air1.services.leadgen.models import (
    DetectionResult,
    DiscoveredBusiness,
    SearchParams,
    SearchStats,
    SoftwareProduct,
)


@pytest.mark.unit
class TestSoftwareProduct:
    def test_defaults(self):
        p = SoftwareProduct(name="Test", slug="test")
        assert p.id == 0
        assert p.website is None
        assert p.detection_patterns == {}

    def test_full(self):
        p = SoftwareProduct(
            id=5,
            name="Cloudbeds",
            slug="cloudbeds",
            website="https://cloudbeds.com",
            detection_patterns={"domains": ["cloudbeds.com"]},
        )
        assert p.id == 5
        assert p.name == "Cloudbeds"
        assert p.slug == "cloudbeds"
        assert p.website == "https://cloudbeds.com"
        assert "domains" in p.detection_patterns


@pytest.mark.unit
class TestSearchParams:
    def test_defaults(self):
        p = SearchParams(center_lat=25.0, center_lng=-80.0)
        assert p.radius_km == 25.0
        assert p.business_type == "business"
        assert p.cell_size_km == 2.0

    def test_custom(self):
        p = SearchParams(
            center_lat=40.7,
            center_lng=-74.0,
            radius_km=10.0,
            business_type="hotel",
            cell_size_km=1.0,
        )
        assert p.center_lat == 40.7
        assert p.radius_km == 10.0
        assert p.business_type == "hotel"

    def test_model_dump(self):
        p = SearchParams(center_lat=25.0, center_lng=-80.0)
        d = p.model_dump()
        assert d["center_lat"] == 25.0
        assert d["center_lng"] == -80.0
        assert "radius_km" in d


@pytest.mark.unit
class TestDiscoveredBusiness:
    def test_minimal(self):
        b = DiscoveredBusiness(name="Hotel ABC")
        assert b.name == "Hotel ABC"
        assert b.website is None
        assert b.source == "serper_maps"

    def test_full(self):
        b = DiscoveredBusiness(
            name="Grand Hotel",
            website="https://grandhotel.com",
            phone="+1-555-0100",
            email="info@grandhotel.com",
            address="123 Main St",
            city="Miami",
            state="FL",
            country="US",
            latitude=25.76,
            longitude=-80.19,
            google_place_id="ChIJ_abc123",
            source="serper_maps",
        )
        assert b.city == "Miami"
        assert b.latitude == 25.76
        assert b.google_place_id == "ChIJ_abc123"


@pytest.mark.unit
class TestDetectionResult:
    def test_defaults_not_detected(self):
        r = DetectionResult()
        assert r.detected is False
        assert r.software_name == ""
        assert r.method == ""
        assert r.confidence == 0.0
        assert r.error == ""

    def test_detected(self):
        r = DetectionResult(
            detected=True,
            software_name="Cloudbeds",
            method="html_pattern",
            confidence=0.9,
            booking_url="https://hotels.cloudbeds.com/reservation/abc",
        )
        assert r.detected is True
        assert r.software_name == "Cloudbeds"
        assert r.confidence == 0.9

    def test_error(self):
        r = DetectionResult(error="timeout")
        assert r.detected is False
        assert r.error == "timeout"


@pytest.mark.unit
class TestSearchStats:
    def test_defaults(self):
        s = SearchStats()
        assert s.businesses_found == 0
        assert s.detected_count == 0
        assert s.api_calls == 0

    def test_model_dump(self):
        s = SearchStats(businesses_found=50, detected_count=10, api_calls=25)
        d = s.model_dump()
        assert d["businesses_found"] == 50
        assert d["detected_count"] == 10
