from ..services.linkedin.service import Service


def run():
    profile_id = "alialabbassi"

    print("Fetching LinkedIn profile...")
    service = Service()
    profile = service.get_profile_info(profile_id, headless=False)

    print("\nProfile Information:")
    print(f"Name: {profile.full_name or 'Not found'}")
    print(f"First Name: {profile.first_name or 'Not found'}")
    print(f"Last Name: {profile.last_name or 'Not found'}")
    print(f"Headline: {profile.headline or 'Not found'}")
    print(f"Location: {profile.location or 'Not found'}")
    print(f"Email: {profile.email or 'Not found'}")
    print(f"Phone: {profile.phone_number or 'Not found'}")


if __name__ == "__main__":
    run()
