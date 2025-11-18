from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LeadRecord(BaseModel):
    """Database record for a lead"""

    lead_id: int
    first_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    created_on: datetime
    updated_on: datetime


class LinkedinProfileRecord(BaseModel):
    """Database record for a LinkedIn profile"""

    linkedin_profile_id: int
    lead_id: int
    username: str
    location: Optional[str] = None
    headline: Optional[str] = None
    about: Optional[str] = None
    created_on: datetime
    updated_on: datetime


class LinkedinCompanyMemberRecord(BaseModel):
    """Database record for a LinkedIn company member"""

    company_member_id: int
    linkedin_profile_id: int
    username: str
    title: Optional[str] = None
    created_on: datetime
    updated_on: datetime


class CompanyLeadRecord(BaseModel):
    """Combined record for company lead queries"""
    lead_id: int
    first_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: str
    headline: Optional[str] = None
    company_name: str
