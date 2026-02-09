import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from air1.services.ingest.sec_client import SECClient
from air1.services.ingest.models import SecFormDData


def _make_address(**kwargs):
    addr = MagicMock()
    addr.street1 = kwargs.get("street1")
    addr.city = kwargs.get("city")
    addr.state_or_country = kwargs.get("state_or_country")
    addr.zipcode = kwargs.get("zipcode")
    return addr


def _make_issuer(**kwargs):
    issuer = MagicMock()
    issuer.entity_name = kwargs.get("entity_name", "Test Corp")
    issuer.jurisdiction = kwargs.get("jurisdiction", "DE")
    issuer.entity_type = kwargs.get("entity_type", "Corporation")
    issuer.phone_number = kwargs.get("phone_number", "555-0100")
    issuer.primary_address = kwargs.get("primary_address", _make_address(
        street1="123 Main St", city="Wilmington", state_or_country="DE", zipcode="19801"
    ))
    return issuer


def _make_offering(**kwargs):
    offering = MagicMock()
    osa = MagicMock()
    osa.total_offering_amount = kwargs.get("total_offering_amount", 1000000)
    osa.total_amount_sold = kwargs.get("total_amount_sold", 500000)
    osa.total_remaining = kwargs.get("total_remaining", 500000)
    offering.offering_sales_amounts = osa
    offering.date_of_first_sale = kwargs.get("date_of_first_sale", "2025-01-15")
    offering.revenue_range = kwargs.get("revenue_range", "$1-$5M")

    ig = MagicMock()
    ig.industry_group_type = kwargs.get("industry_group_type", "Technology")
    offering.industry_group = ig

    offering.federal_exemptions = kwargs.get("federal_exemptions", ["06b", "3C.1"])
    return offering


def _make_person(first_name="Jane", last_name="Smith", address=None):
    person = MagicMock()
    person.first_name = first_name
    person.last_name = last_name
    person.address = address or _make_address(
        street1="456 Oak Ave", city="SF", state_or_country="CA", zipcode="94102"
    )
    return person


def _make_form_d(issuer=None, offering=None, persons=None):
    form_d = MagicMock()
    form_d.primary_issuer = issuer
    form_d.offering_data = offering
    form_d.related_persons = persons or []
    return form_d


@pytest.mark.unit
class TestParseFormD:
    def test_full_parse(self):
        form_d = _make_form_d(
            issuer=_make_issuer(),
            offering=_make_offering(),
            persons=[_make_person(), _make_person(first_name="Bob", last_name="Jones")],
        )
        result = SECClient._parse_form_d(form_d, "acc-001", "12345", date(2025, 1, 15))

        assert isinstance(result, SecFormDData)
        assert result.accession_number == "acc-001"
        assert result.cik == "12345"
        assert result.filing_date == date(2025, 1, 15)
        assert result.issuer_name == "Test Corp"
        assert result.issuer_street == "123 Main St"
        assert result.issuer_city == "Wilmington"
        assert result.issuer_state == "DE"
        assert result.issuer_zip == "19801"
        assert result.issuer_phone == "555-0100"
        assert result.entity_type == "Corporation"
        assert result.industry_group_type == "Technology"
        assert result.revenue_range == "$1-$5M"
        assert result.federal_exemptions == "06b,3C.1"
        assert result.total_offering_amount == Decimal("1000000")
        assert result.total_amount_sold == Decimal("500000")
        assert result.total_remaining == Decimal("500000")
        assert result.date_of_first_sale == date(2025, 1, 15)
        assert len(result.officers) == 2
        assert result.officers[0].first_name == "Jane"
        assert result.officers[1].first_name == "Bob"

    def test_no_issuer(self):
        form_d = _make_form_d(issuer=None, offering=_make_offering())
        result = SECClient._parse_form_d(form_d, "acc-002", "99", date(2025, 3, 1))

        assert result.issuer_name is None
        assert result.issuer_phone is None
        assert result.entity_type is None

    def test_no_offering(self):
        form_d = _make_form_d(issuer=_make_issuer(), offering=None)
        result = SECClient._parse_form_d(form_d, "acc-003", "99", date(2025, 3, 1))

        assert result.total_offering_amount is None
        assert result.total_amount_sold is None
        assert result.revenue_range is None
        assert result.industry_group_type is None
        assert result.federal_exemptions is None
        assert result.date_of_first_sale is None

    def test_no_officers(self):
        form_d = _make_form_d(
            issuer=_make_issuer(), offering=_make_offering(), persons=[]
        )
        result = SECClient._parse_form_d(form_d, "acc-004", "99", date(2025, 3, 1))

        assert result.officers == []

    def test_none_related_persons(self):
        form_d = _make_form_d(issuer=_make_issuer(), offering=_make_offering())
        form_d.related_persons = None
        result = SECClient._parse_form_d(form_d, "acc-005", "99", date(2025, 3, 1))

        assert result.officers == []

    def test_date_of_first_sale_yet_to_occur(self):
        offering = _make_offering(date_of_first_sale="Yet to occur")
        form_d = _make_form_d(issuer=_make_issuer(), offering=offering)
        result = SECClient._parse_form_d(form_d, "acc-006", "99", date(2025, 3, 1))

        assert result.date_of_first_sale is None

    def test_date_of_first_sale_none(self):
        offering = _make_offering(date_of_first_sale=None)
        form_d = _make_form_d(issuer=_make_issuer(), offering=offering)
        result = SECClient._parse_form_d(form_d, "acc-007", "99", date(2025, 3, 1))

        assert result.date_of_first_sale is None

    def test_invalid_offering_amounts(self):
        offering = _make_offering(
            total_offering_amount="not-a-number",
            total_amount_sold=None,
            total_remaining="",
        )
        form_d = _make_form_d(issuer=_make_issuer(), offering=offering)
        result = SECClient._parse_form_d(form_d, "acc-008", "99", date(2025, 3, 1))

        assert result.total_offering_amount is None
        assert result.total_amount_sold is None
        assert result.total_remaining is None

    def test_filing_date_as_string(self):
        form_d = _make_form_d(issuer=_make_issuer(), offering=_make_offering())
        result = SECClient._parse_form_d(form_d, "acc-009", "99", "2025-06-15")

        assert result.filing_date == date(2025, 6, 15)

    def test_officer_without_address(self):
        person = _make_person()
        person.address = None
        form_d = _make_form_d(
            issuer=_make_issuer(), offering=_make_offering(), persons=[person]
        )
        result = SECClient._parse_form_d(form_d, "acc-010", "99", date(2025, 3, 1))

        assert len(result.officers) == 1
        assert result.officers[0].first_name == "Jane"
        assert result.officers[0].street is None
        assert result.officers[0].city is None

    def test_no_offering_sales_amounts(self):
        offering = _make_offering()
        offering.offering_sales_amounts = None
        form_d = _make_form_d(issuer=_make_issuer(), offering=offering)
        result = SECClient._parse_form_d(form_d, "acc-011", "99", date(2025, 3, 1))

        assert result.total_offering_amount is None
        assert result.total_amount_sold is None

    def test_issuer_without_primary_address(self):
        issuer = _make_issuer()
        issuer.primary_address = None
        form_d = _make_form_d(issuer=issuer, offering=_make_offering())
        result = SECClient._parse_form_d(form_d, "acc-012", "99", date(2025, 3, 1))

        assert result.issuer_name == "Test Corp"
        assert result.issuer_street is None
        assert result.issuer_city is None
        assert result.issuer_zip is None

    def test_no_federal_exemptions(self):
        offering = _make_offering(federal_exemptions=None)
        form_d = _make_form_d(issuer=_make_issuer(), offering=offering)
        result = SECClient._parse_form_d(form_d, "acc-013", "99", date(2025, 3, 1))

        assert result.federal_exemptions is None

    def test_no_industry_group(self):
        offering = _make_offering()
        offering.industry_group = None
        form_d = _make_form_d(issuer=_make_issuer(), offering=offering)
        result = SECClient._parse_form_d(form_d, "acc-014", "99", date(2025, 3, 1))

        assert result.industry_group_type is None
