from typing import Optional

from pydantic import BaseModel


class ProfileExperience(BaseModel):
    title: str = ""
    company_id: Optional[str] = None
    start_date: Optional[str] = None


class LinkedinProfile(BaseModel):
    first_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""
    username: str = ""
    location: str = ""
    headline: str = ""
    about: str = ""
    experiences: list["ProfileExperience"] = []


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
    """Add username to profile

    Deprecated: get_profile_info now sets the username directly.
    """
    profile.username = username
    return profile


def get_current_company_info(
    profile: LinkedinProfile,
) -> tuple[Optional[str], Optional[str]]:
    """Extract current company info from profile experiences.

    The first experience entry is typically the current job.

    Args:
        profile: LinkedinProfile with experiences

    Returns:
        Tuple of (company_id, job_title) - both may be None if no experiences
    """
    if not profile.experiences:
        return None, None

    current_experience = profile.experiences[0]
    return current_experience.company_id, current_experience.title
