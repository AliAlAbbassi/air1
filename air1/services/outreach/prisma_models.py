from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CompanyLeadRecord(BaseModel):
    """Combined record for company lead queries using Prisma"""
    lead_id: int
    first_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: str
    headline: Optional[str] = None
    company_name: str