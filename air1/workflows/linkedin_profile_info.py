from ..services.browser.service import Service
from loguru import logger


def run():
    profile_id = "alialabbassi"

    logger.info("Fetching LinkedIn profile...")
    service = Service()
    profile = service.get_profile_info(profile_id, headless=False)

    logger.info("Profile Information:")
    logger.info(f"Name: {profile.full_name or 'Not found'}")
    logger.info(f"First Name: {profile.first_name or 'Not found'}")
    logger.info(f"Last Name: {profile.last_name or 'Not found'}")
    logger.info(f"Headline: {profile.headline or 'Not found'}")
    logger.info(f"Location: {profile.location or 'Not found'}")
    logger.info(f"Email: {profile.email or 'Not found'}")
    logger.info(f"Phone: {profile.phone_number or 'Not found'}")


if __name__ == "__main__":
    run()
