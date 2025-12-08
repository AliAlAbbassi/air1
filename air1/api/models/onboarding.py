from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import re


class AuthMethod(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"


class EmployeeCount(str, Enum):
    TINY = "0-10"
    SMALL = "10-100"
    MEDIUM = "100-500"
    LARGE = "500-1000"
    ENTERPRISE = "1000+"


class AuthData(BaseModel):
    method: AuthMethod
    email: EmailStr
    first_name: str = Field(..., alias="firstName", min_length=1)
    last_name: str = Field(..., alias="lastName", min_length=1)
    password: Optional[str] = Field(None, min_length=8)
    google_access_token: Optional[str] = Field(None, alias="googleAccessToken")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_auth_method(self):
        if self.method == AuthMethod.EMAIL and not self.password:
            raise ValueError("Password is required for email authentication")
        if self.method == AuthMethod.GOOGLE and not self.google_access_token:
            raise ValueError("Google access token is required for Google authentication")
        return self


class CompanyData(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    website: str = Field(..., min_length=1)
    industry: str = Field(..., min_length=1)
    linkedin_url: str = Field(..., alias="linkedinUrl")
    employee_count: EmployeeCount = Field(..., alias="employeeCount")

    model_config = {"populate_by_name": True}

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: str) -> str:
        if not re.match(r"^https?://", v):
            raise ValueError("Website must be a valid URL starting with http:// or https://")
        return v

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: str) -> str:
        if not re.match(r"^https?://(www\.)?linkedin\.com/company/", v):
            raise ValueError("Must be a valid LinkedIn company URL")
        return v


class ProductData(BaseModel):
    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    ideal_customer_profile: str = Field(..., alias="idealCustomerProfile", min_length=1)
    competitors: Optional[str] = None

    model_config = {"populate_by_name": True}

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not re.match(r"^https?://", v):
            raise ValueError("Product URL must be a valid URL")
        return v


class WritingStyleData(BaseModel):
    selected_template: Optional[str] = Field(None, alias="selectedTemplate")
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class LinkedinData(BaseModel):
    connected: bool


class ProfileData(BaseModel):
    # Note: fullName removed - computed from auth.firstName + auth.lastName
    timezone: str = Field(..., min_length=1)
    meeting_link: str = Field(..., alias="meetingLink")

    model_config = {"populate_by_name": True}

    @field_validator("meeting_link")
    @classmethod
    def validate_meeting_link(cls, v: str) -> str:
        if not re.match(r"^https?://", v):
            raise ValueError("Meeting link must be a valid URL")
        return v


class OnboardingRequest(BaseModel):
    auth: AuthData
    company: CompanyData
    product: ProductData
    writing_style: WritingStyleData = Field(..., alias="writingStyle")
    linkedin: LinkedinData
    profile: ProfileData

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")

    model_config = {"populate_by_name": True, "by_alias": True}


class OnboardingResponse(BaseModel):
    user: UserResponse
    token: str


class ValidationErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[list[ValidationErrorDetail]] = None


class CompanyFetchRequest(BaseModel):
    linkedin_url: str = Field(..., alias="linkedinUrl")

    model_config = {"populate_by_name": True}

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: str) -> str:
        if not re.match(r"^https?://(www\.)?linkedin\.com/company/", v):
            raise ValueError("Must be a valid LinkedIn company URL")
        return v


class CompanyFetchResponse(BaseModel):
    name: str
    description: str
    website: str
    industry: str
    logo: Optional[str] = None
