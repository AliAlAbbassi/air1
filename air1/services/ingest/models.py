"""Data models for SEC EDGAR ingestion."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class SecCompanyData(BaseModel):
    """Company data from SEC EDGAR ticker file."""

    cik: str
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None


class SecCompanyProfile(BaseModel):
    """Enriched company profile from SEC submissions endpoint."""

    cik: str
    name: str
    sic: Optional[str] = None
    sic_description: Optional[str] = None
    state_of_incorp: Optional[str] = None
    fiscal_year_end: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state_or_country: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class SecFilingData(BaseModel):
    """Filing metadata from SEC."""

    accession_number: str
    cik: str
    form_type: str
    filing_date: date
    company_name: Optional[str] = None
    primary_document: Optional[str] = None
    description: Optional[str] = None


class SecOfficerData(BaseModel):
    """Officer/director data from Form D."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class SecFormDData(BaseModel):
    """Parsed Form D filing data."""

    accession_number: str
    cik: str
    filing_date: date
    issuer_name: Optional[str] = None
    issuer_street: Optional[str] = None
    issuer_city: Optional[str] = None
    issuer_state: Optional[str] = None
    issuer_zip: Optional[str] = None
    issuer_phone: Optional[str] = None
    entity_type: Optional[str] = None
    industry_group_type: Optional[str] = None
    revenue_range: Optional[str] = None
    federal_exemptions: Optional[str] = None
    total_offering_amount: Optional[Decimal] = None
    total_amount_sold: Optional[Decimal] = None
    total_remaining: Optional[Decimal] = None
    date_of_first_sale: Optional[date] = None
    officers: list[SecOfficerData] = []
