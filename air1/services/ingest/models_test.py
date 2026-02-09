import pytest
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from air1.services.ingest.models import (
    SecCompanyData,
    SecCompanyProfile,
    SecFilingData,
    SecFormDData,
    SecOfficerData,
)


@pytest.mark.unit
class TestSecCompanyData:
    def test_required_fields(self):
        c = SecCompanyData(cik="12345", name="Acme Corp")
        assert c.cik == "12345"
        assert c.name == "Acme Corp"
        assert c.ticker is None
        assert c.exchange is None

    def test_all_fields(self):
        c = SecCompanyData(cik="12345", name="Acme", ticker="ACME", exchange="NYSE")
        assert c.ticker == "ACME"
        assert c.exchange == "NYSE"

    def test_missing_cik_raises(self):
        with pytest.raises(ValidationError):
            SecCompanyData(name="Acme")

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            SecCompanyData(cik="12345")


@pytest.mark.unit
class TestSecCompanyProfile:
    def test_minimal(self):
        p = SecCompanyProfile(cik="1", name="X")
        assert p.sic is None
        assert p.phone is None
        assert p.website is None

    def test_full(self):
        p = SecCompanyProfile(
            cik="1", name="X", sic="7372", sic_description="Software",
            state_of_incorp="DE", fiscal_year_end="1231",
            street="123 Main", city="NY", state_or_country="NY",
            zip_code="10001", phone="555-1234", website="https://x.com",
        )
        assert p.sic == "7372"
        assert p.website == "https://x.com"


@pytest.mark.unit
class TestSecFilingData:
    def test_required_fields(self):
        f = SecFilingData(
            accession_number="0001-24-001",
            cik="12345",
            form_type="D",
            filing_date=date(2025, 1, 15),
        )
        assert f.company_name is None

    def test_date_coercion_from_string(self):
        f = SecFilingData(
            accession_number="acc",
            cik="1",
            form_type="D",
            filing_date="2025-06-01",
        )
        assert f.filing_date == date(2025, 6, 1)

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            SecFilingData(cik="1", form_type="D", filing_date=date(2025, 1, 1))


@pytest.mark.unit
class TestSecFormDData:
    def test_defaults(self):
        f = SecFormDData(
            accession_number="acc", cik="1", filing_date=date(2025, 1, 1)
        )
        assert f.officers == []
        assert f.total_offering_amount is None
        assert f.issuer_name is None

    def test_with_officers(self):
        f = SecFormDData(
            accession_number="acc",
            cik="1",
            filing_date=date(2025, 1, 1),
            officers=[
                SecOfficerData(first_name="John", last_name="Doe"),
                SecOfficerData(first_name="Jane", last_name="Smith"),
            ],
        )
        assert len(f.officers) == 2

    def test_decimal_amounts(self):
        f = SecFormDData(
            accession_number="acc",
            cik="1",
            filing_date=date(2025, 1, 1),
            total_offering_amount=Decimal("1000000.50"),
            total_amount_sold=Decimal("500000.25"),
            total_remaining=Decimal("500000.25"),
        )
        assert f.total_offering_amount == Decimal("1000000.50")


@pytest.mark.unit
class TestSecOfficerData:
    def test_all_none(self):
        o = SecOfficerData()
        assert o.first_name is None
        assert o.last_name is None
        assert o.title is None

    def test_with_values(self):
        o = SecOfficerData(
            first_name="John", last_name="Doe", title="CEO",
            street="123 Main", city="NY", state="NY", zip_code="10001"
        )
        assert o.title == "CEO"
