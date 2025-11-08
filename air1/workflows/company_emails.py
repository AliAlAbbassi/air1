from ..services.linkedin.service import Service


def run():
    print("workflow: company emails")
    service = Service()
    session = service.launch_browser(headless=False)
    company = "forsythbarnes"

    try:
        company_people = session.get_company_members(company, limit=10)
        print(f"Found {len(company_people.profile_ids)} profiles")

        for profile_id in company_people.profile_ids:
            profile = session.get_profile_info(profile_id)
            if profile.isTalent():
                print(profile)
                print("this is talent")
                break
    finally:
        session.browser.close()

    print("yeet")


if __name__ == "__main__":
    run()
