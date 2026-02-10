import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from air1.services.ingest.models import (
    SecCompanyData,
    SecCompanyProfile,
    SecFilingData,
    SecFormDData,
    SecOfficerData,
)
from air1.services.ingest.service import Service


@pytest.fixture
def mock_client():
    client = AsyncMock()
    return client


@pytest.fixture
def service(mock_client):
    svc = Service(identity="Test test@test.com")
    svc._client = mock_client
    return svc


@pytest.mark.asyncio
@pytest.mark.unit
async def test_bootstrap_companies(service, mock_client):
    companies = [
        SecCompanyData(cik="1234", name="Acme Corp", ticker="ACME", exchange="NYSE"),
        SecCompanyData(cik="5678", name="Foo Inc", ticker="FOO", exchange="NASDAQ"),
    ]
    mock_client.fetch_company_tickers.return_value = companies

    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.upsert_companies_batch = AsyncMock(return_value=2)
        result = await service.bootstrap_companies()

    assert result == 2
    mock_client.fetch_company_tickers.assert_awaited_once()
    mock_repo.upsert_companies_batch.assert_awaited_once_with(companies)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_bootstrap_companies_partial_failures(service, mock_client):
    companies = [
        SecCompanyData(cik="1", name="A"),
        SecCompanyData(cik="2", name="B"),
        SecCompanyData(cik="3", name="C"),
    ]
    mock_client.fetch_company_tickers.return_value = companies

    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.upsert_companies_batch = AsyncMock(return_value=1)
        result = await service.bootstrap_companies()

    assert result == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_companies(service, mock_client):
    unenriched = [
        {"secCompanyId": 1, "cik": "1234", "name": "Acme", "ticker": "ACME", "exchange": "NYSE"},
        {"secCompanyId": 2, "cik": "5678", "name": "Foo", "ticker": "FOO", "exchange": "NASDAQ"},
    ]
    mock_client.fetch_company_profile.return_value = SecCompanyProfile(
        cik="1234", name="Acme Corp", sic="7372", phone="555-1234"
    )

    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.get_companies_not_enriched = AsyncMock(return_value=unenriched)
        mock_repo.enrich_companies_batch = AsyncMock(return_value=2)
        result = await service.enrich_companies(batch_size=10)

    assert result == 2
    assert mock_client.fetch_company_profile.await_count == 2
    mock_repo.enrich_companies_batch.assert_awaited_once()
    profiles = mock_repo.enrich_companies_batch.call_args[0][0]
    assert len(profiles) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_companies_empty(service, mock_client):
    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.get_companies_not_enriched = AsyncMock(return_value=[])
        result = await service.enrich_companies()

    assert result == 0
    mock_client.fetch_company_profile.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_companies_skips_failures(service, mock_client):
    unenriched = [
        {"secCompanyId": 1, "cik": "1", "name": "A", "ticker": None, "exchange": None},
        {"secCompanyId": 2, "cik": "2", "name": "B", "ticker": None, "exchange": None},
        {"secCompanyId": 3, "cik": "3", "name": "C", "ticker": None, "exchange": None},
    ]
    mock_client.fetch_company_profile.side_effect = [
        SecCompanyProfile(cik="1", name="A"),
        Exception("API error"),
        SecCompanyProfile(cik="3", name="C"),
    ]

    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.get_companies_not_enriched = AsyncMock(return_value=unenriched)
        mock_repo.enrich_companies_batch = AsyncMock(return_value=2)
        result = await service.enrich_companies()

    assert result == 2
    # Only 2 profiles fetched successfully, so batch should receive 2
    profiles = mock_repo.enrich_companies_batch.call_args[0][0]
    assert len(profiles) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_ingest_form_d_filings(service, mock_client):
    filings = [
        SecFilingData(
            accession_number="0001-24-001",
            cik="1234",
            form_type="D",
            filing_date=date(2025, 1, 15),
            company_name="Startup Inc",
        ),
    ]
    mock_client.fetch_form_d_filings.return_value = filings

    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.upsert_filings_batch = AsyncMock(return_value=1)
        result = await service.ingest_form_d_filings(
            date_start="2025-01-01", date_end="2025-01-31"
        )

    assert result == 1
    mock_client.fetch_form_d_filings.assert_awaited_once_with("2025-01-01", "2025-01-31")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_ingest_form_d_filings_default_dates(service, mock_client):
    mock_client.fetch_form_d_filings.return_value = []

    with patch("air1.services.ingest.service.repo"):
        result = await service.ingest_form_d_filings(days=7)

    assert result == 0
    call_args = mock_client.fetch_form_d_filings.call_args
    assert call_args is not None
    start, end = call_args[0]
    assert end == date.today().isoformat()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_ingest_form_d_empty_result(service, mock_client):
    mock_client.fetch_form_d_filings.return_value = []

    with patch("air1.services.ingest.service.repo") as mock_repo:
        result = await service.ingest_form_d_filings(
            date_start="2025-01-01", date_end="2025-01-31"
        )

    assert result == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_form_d_details(service, mock_client):
    unparsed = [
        {"secFilingId": 1, "accessionNumber": "0001-24-001", "cik": "1234",
         "formType": "D", "filingDate": "2025-01-15", "companyName": "Startup Inc"},
    ]
    form_d = SecFormDData(
        accession_number="0001-24-001",
        cik="1234",
        filing_date=date(2025, 1, 15),
        issuer_name="Startup Inc",
        officers=[
            SecOfficerData(first_name="John", last_name="Doe", title="CEO"),
        ],
    )
    mock_client.fetch_form_d_detail.return_value = form_d

    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.get_form_d_filings_not_parsed = AsyncMock(return_value=unparsed)
        mock_repo.upsert_companies_from_issuers_batch = AsyncMock(return_value=1)
        mock_repo.save_form_d_batch = AsyncMock(return_value=1)
        mock_repo.link_orphaned_filings = AsyncMock()
        result = await service.parse_form_d_details(batch_size=50)

    assert result == 1
    mock_client.fetch_form_d_detail.assert_awaited_once_with("0001-24-001")
    mock_repo.upsert_companies_from_issuers_batch.assert_awaited_once()
    issuers = mock_repo.upsert_companies_from_issuers_batch.call_args[0][0]
    assert len(issuers) == 1
    assert issuers[0][0] == "1234"  # cik
    mock_repo.save_form_d_batch.assert_awaited_once()
    items = mock_repo.save_form_d_batch.call_args[0][0]
    assert len(items) == 1
    assert items[0] == (form_d, 1)
    mock_repo.link_orphaned_filings.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_form_d_empty(service, mock_client):
    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.get_form_d_filings_not_parsed = AsyncMock(return_value=[])
        result = await service.parse_form_d_details()

    assert result == 0
    mock_client.fetch_form_d_detail.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_form_d_skips_failures(service, mock_client):
    unparsed = [
        {"secFilingId": 1, "accessionNumber": "acc-1", "cik": "1",
         "formType": "D", "filingDate": "2025-01-01", "companyName": "A"},
        {"secFilingId": 2, "accessionNumber": "acc-2", "cik": "2",
         "formType": "D", "filingDate": "2025-01-02", "companyName": "B"},
    ]
    mock_client.fetch_form_d_detail.side_effect = [
        Exception("Parse error"),
        SecFormDData(accession_number="acc-2", cik="2", filing_date=date(2025, 1, 2)),
    ]

    with patch("air1.services.ingest.service.repo") as mock_repo:
        mock_repo.get_form_d_filings_not_parsed = AsyncMock(return_value=unparsed)
        mock_repo.upsert_companies_from_issuers_batch = AsyncMock(return_value=0)
        mock_repo.save_form_d_batch = AsyncMock(return_value=1)
        mock_repo.link_orphaned_filings = AsyncMock()
        result = await service.parse_form_d_details()

    # Only 1 form_d fetched successfully (acc-2), so batch gets 1 item
    assert result == 1
    items = mock_repo.save_form_d_batch.call_args[0][0]
    assert len(items) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_service_context_manager():
    with patch("air1.services.ingest.service.SECClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        async with Service(identity="Test test@test.com") as svc:
            assert svc._client is mock_instance

        assert svc._client is None
