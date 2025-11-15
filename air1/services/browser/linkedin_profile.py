from pydantic import BaseModel


class LinkedinProfile(BaseModel):
    first_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""
    username: str = ""
    location: str = ""
    headline: str = ""
    about: str = ""


class CompanyPeople(BaseModel):
    profile_ids: set[str]


class Lead(BaseModel):
    first_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""


def profile_to_lead(profile: LinkedinProfile) -> Lead:
    """Convert LinkedinProfile to Lead"""
    return Lead(
        first_name=profile.first_name,
        full_name=profile.full_name,
        email=profile.email,
        phone_number=profile.phone_number,
    )


def enrich_profile_with_username(
    profile: LinkedinProfile, username: str
) -> LinkedinProfile:
    """Add username to profile"""
    profile.username = username
    return profile
