"""Unit tests for built-in detection patterns."""

import pytest

from air1.services.leadgen.patterns import BUILTIN_PATTERNS


@pytest.mark.unit
class TestBuiltinPatterns:
    def test_has_expected_slugs(self):
        expected = {"cloudbeds", "shopify", "wordpress", "squarespace", "wix"}
        assert expected.issubset(set(BUILTIN_PATTERNS.keys()))

    def test_all_have_required_fields(self):
        for slug, entry in BUILTIN_PATTERNS.items():
            assert "name" in entry, f"{slug} missing 'name'"
            assert "detection_patterns" in entry, f"{slug} missing 'detection_patterns'"
            patterns = entry["detection_patterns"]
            assert "domains" in patterns, f"{slug} missing 'domains'"
            assert "url_patterns" in patterns, f"{slug} missing 'url_patterns'"
            assert "html_patterns" in patterns, f"{slug} missing 'html_patterns'"

    def test_patterns_are_lists(self):
        for slug, entry in BUILTIN_PATTERNS.items():
            patterns = entry["detection_patterns"]
            assert isinstance(patterns["domains"], list), f"{slug} domains not a list"
            assert isinstance(patterns["url_patterns"], list), f"{slug} url_patterns not a list"
            assert isinstance(patterns["html_patterns"], list), f"{slug} html_patterns not a list"

    def test_cloudbeds_patterns(self):
        cb = BUILTIN_PATTERNS["cloudbeds"]
        assert cb["name"] == "Cloudbeds"
        assert "cloudbeds.com" in cb["detection_patterns"]["domains"]

    def test_shopify_patterns(self):
        sp = BUILTIN_PATTERNS["shopify"]
        assert sp["name"] == "Shopify"
        assert "cdn.shopify.com" in sp["detection_patterns"]["html_patterns"]

    def test_wordpress_has_no_domains(self):
        wp = BUILTIN_PATTERNS["wordpress"]
        assert wp["detection_patterns"]["domains"] == []
        assert "wp-content/" in wp["detection_patterns"]["html_patterns"]

    def test_all_have_at_least_one_html_pattern(self):
        for slug, entry in BUILTIN_PATTERNS.items():
            assert len(entry["detection_patterns"]["html_patterns"]) > 0, (
                f"{slug} has no html_patterns"
            )
