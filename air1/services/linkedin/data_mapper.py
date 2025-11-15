from .linkedin_profile import LinkedinProfile, Lead


class DataMapper:
    """Handles data transformation between different models"""

    @staticmethod
    def profile_to_lead(profile: LinkedinProfile) -> Lead:
        """Convert LinkedinProfile to Lead"""
        return Lead(
            first_name=profile.first_name,
            full_name=profile.full_name,
            email=profile.email,
            phone_number=profile.phone_number,
        )

    @staticmethod
    def enrich_profile_with_username(profile: LinkedinProfile, username: str) -> LinkedinProfile:
        """Add username to profile"""
        profile.username = username
        return profile