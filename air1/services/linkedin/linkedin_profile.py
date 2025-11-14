from pydantic import BaseModel


class LinkedinProfile(BaseModel):
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""
    linkedin_url: str = ""  # Keep for backward compatibility in scraping
    username: str = ""      # New field for database storage
    location: str = ""
    headline: str = ""
    about: str = ""
    lead_id: str = ""


class CompanyPeople(BaseModel):
    profile_ids: set[str]


class Lead(BaseModel):
    first_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""
