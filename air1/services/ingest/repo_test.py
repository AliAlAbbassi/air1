import pytest
import uuid
from datetime import date
from decimal import Decimal

from air1.db.prisma_client import connect_db, disconnect_db
from air1.services.ingest.models import (
    SecCompanyData,
    SecCompanyProfile,
    SecFilingData,
    SecFormDData,
    SecOfficerData,
)
from air1.services.ingest.repo import (
    count_companies,
    count_companies_not_enriched,
    enrich_company,
    get_companies_not_enriched,
    get_form_d_filings_not_parsed,
    save_form_d_complete,
    upsert_company,
    upsert_companies_batch,
    upsert_filing,
)


@pytest.fixture(autouse=True)
async def db():
    await connect_db()
    yield
    await disconnect_db()


def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ── sec_company ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upsert_company():
    cik = f"T{_uid()}"
    company = SecCompanyData(cik=cik, name="Test Corp", ticker="TST", exchange="NYSE")

    ok, company_id = await upsert_company(company)
    assert ok is True
    assert company_id is not None

    # Upsert again with updated name
    company2 = SecCompanyData(cik=cik, name="Test Corp Updated", ticker="TST2")
    ok2, company_id2 = await upsert_company(company2)
    assert ok2 is True
    assert company_id2 == company_id  # same row


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upsert_companies_batch():
    prefix = _uid()
    companies = [
        SecCompanyData(cik=f"B{prefix}1", name="Batch A"),
        SecCompanyData(cik=f"B{prefix}2", name="Batch B"),
        SecCompanyData(cik=f"B{prefix}3", name="Batch C"),
    ]
    count = await upsert_companies_batch(companies)
    assert count == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_company():
    cik = f"E{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Enrich Me"))

    profile = SecCompanyProfile(
        cik=cik,
        name="Enrich Me",
        sic="7372",
        sic_description="Prepackaged Software",
        state_of_incorp="DE",
        phone="555-9999",
        website="https://enrichme.com",
    )
    ok = await enrich_company(profile)
    assert ok is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_companies_not_enriched():
    cik = f"U{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Unenriched Co"))

    rows = await get_companies_not_enriched(limit=50000)
    ciks = [r["cik"] for r in rows]
    assert cik in ciks


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enriched_company_excluded_from_not_enriched():
    cik = f"X{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Will Enrich"))
    await enrich_company(SecCompanyProfile(cik=cik, name="Will Enrich", sic="1234"))

    rows = await get_companies_not_enriched(limit=10000)
    ciks = [r["cik"] for r in rows]
    assert cik not in ciks


@pytest.mark.asyncio
@pytest.mark.unit
async def test_count_companies():
    cik = f"C{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Countable"))

    total = await count_companies()
    assert total >= 1

    not_enriched = await count_companies_not_enriched()
    assert not_enriched >= 1


# ── sec_filing ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upsert_filing():
    cik = f"F{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Filing Co"))

    acc = f"0001-{_uid()}"
    filing = SecFilingData(
        accession_number=acc,
        cik=cik,
        form_type="D",
        filing_date=date(2025, 6, 1),
        company_name="Filing Co",
    )
    ok, filing_id = await upsert_filing(filing)
    assert ok is True
    assert filing_id is not None

    # Upsert same accession number
    ok2, filing_id2 = await upsert_filing(filing)
    assert ok2 is True
    assert filing_id2 == filing_id


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_form_d_filings_not_parsed():
    cik = f"P{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Unparsed Co"))

    acc = f"0002-{_uid()}"
    filing = SecFilingData(
        accession_number=acc,
        cik=cik,
        form_type="D",
        filing_date=date(2025, 6, 1),
        company_name="Unparsed Co",
    )
    await upsert_filing(filing)

    rows = await get_form_d_filings_not_parsed(limit=1000)
    acc_numbers = [r["accessionNumber"] for r in rows]
    assert acc in acc_numbers


# ── sec_form_d + sec_officer ────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_form_d_complete():
    cik = f"D{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="FormD Co"))

    acc = f"0003-{_uid()}"
    _, filing_id = await upsert_filing(
        SecFilingData(
            accession_number=acc,
            cik=cik,
            form_type="D",
            filing_date=date(2025, 6, 1),
            company_name="FormD Co",
        )
    )

    form_d = SecFormDData(
        accession_number=acc,
        cik=cik,
        filing_date=date(2025, 6, 1),
        issuer_name="FormD Co",
        issuer_city="San Francisco",
        issuer_state="CA",
        entity_type="Corporation",
        industry_group_type="Technology",
        revenue_range="$1-$5M",
        total_offering_amount=Decimal("5000000"),
        total_amount_sold=Decimal("2000000"),
        total_remaining=Decimal("3000000"),
        officers=[
            SecOfficerData(first_name="Alice", last_name="CEO", title="Chief Executive Officer"),
            SecOfficerData(first_name="Bob", last_name="CTO", title="Chief Technology Officer"),
        ],
    )
    ok, form_d_id = await save_form_d_complete(form_d, sec_filing_id=filing_id)
    assert ok is True
    assert form_d_id is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parsed_filing_excluded_from_not_parsed():
    cik = f"Z{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Parsed Co"))

    acc = f"0004-{_uid()}"
    _, filing_id = await upsert_filing(
        SecFilingData(
            accession_number=acc, cik=cik, form_type="D",
            filing_date=date(2025, 6, 1), company_name="Parsed Co",
        )
    )
    await save_form_d_complete(
        SecFormDData(accession_number=acc, cik=cik, filing_date=date(2025, 6, 1)),
        sec_filing_id=filing_id,
    )

    rows = await get_form_d_filings_not_parsed(limit=10000)
    acc_numbers = [r["accessionNumber"] for r in rows]
    assert acc not in acc_numbers


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_form_d_upsert_idempotent():
    cik = f"I{_uid()}"
    await upsert_company(SecCompanyData(cik=cik, name="Idempotent Co"))

    acc = f"0005-{_uid()}"
    _, filing_id = await upsert_filing(
        SecFilingData(
            accession_number=acc, cik=cik, form_type="D",
            filing_date=date(2025, 6, 1),
        )
    )

    form_d = SecFormDData(
        accession_number=acc, cik=cik, filing_date=date(2025, 6, 1),
        issuer_name="Idempotent Co", total_offering_amount=Decimal("1000000"),
    )
    ok1, id1 = await save_form_d_complete(form_d, sec_filing_id=filing_id)
    ok2, id2 = await save_form_d_complete(form_d, sec_filing_id=filing_id)
    assert ok1 is True
    assert ok2 is True
    assert id1 == id2
