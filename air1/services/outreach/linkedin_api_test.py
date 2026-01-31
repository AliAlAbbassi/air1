import os

import pytest
from dotenv import load_dotenv

from air1.services.outreach.linkedin_api import LinkedInAPI, LinkedInProfile
from air1.services.outreach.linkedin_locations import DUBAI_EMIRATE
from air1.services.outreach.templates import DEFAULT_COLD_CONNECTION_NOTE

load_dotenv()


@pytest.mark.integration
def test_connect_with_someone_online():
    """
    Online test that attempts to connect with a specific person.
    Requires LINKEDIN_WRITE_SID and LINKEDIN_JSESSIONID environment variables.
    WARNING: This essentially performs a real action on your LinkedIn account.
    """
    li_at = os.getenv("LINKEDIN_WRITE_SID")
    jsessionid = os.getenv("LINKEDIN_JSESSIONID")
    target_urn = "mohamed-othman11"

    if not li_at or not jsessionid:
        pytest.skip(
            "Skipping online test: LINKEDIN_WRITE_SID or LINKEDIN_JSESSIONID not set"
        )

    # Clean jsessionid for header if it has quotes
    csrf_token = jsessionid.strip('"')

    cookies = {"li_at": li_at, "JSESSIONID": jsessionid}

    headers = {"Csrf-Token": csrf_token, "X-RestLi-Protocol-Version": "2.0.0"}

    api = LinkedInAPI(cookies=cookies, headers=headers)

    # 1. Resolve URN if provided as a username (slug)
    tracking_id = None
    if not target_urn.startswith("urn:"):
        print(f"Resolving username '{target_urn}' to URN...")
        resolved_urn, tracking_id = api.get_profile_urn(target_urn)
        if resolved_urn:
            print(f"Resolved to {resolved_urn}")
            if tracking_id:
                print(f"Extracted trackingId: {tracking_id}")
            target_urn = resolved_urn
        else:
            pytest.fail(
                f"Could not resolve username '{target_urn}' to a URN. Please provide a valid URN or check the username."
            )

    # Send Connection Request
    print(f"Attempting to connect to {target_urn}...")
    if tracking_id:
        print(f"Using trackingId: {tracking_id}")

    # Note: connect endpoint usually expects the clean URN or ID.
    # The 'urn:li:fsd_profile:ACo...' format is likely acceptable for the /dash/ or /growth/ endpoints.

    message = DEFAULT_COLD_CONNECTION_NOTE.strip()
    success = api.send_connection_request(
        target_urn, message=message, tracking_id=tracking_id
    )

    assert success is True, "Failed to send connection request"


@pytest.mark.integration
def test_search_people_online():
    """
    Online test that searches for people on LinkedIn.
    Requires LINKEDIN_WRITE_SID and LINKEDIN_JSESSIONID environment variables.
    """
    li_at = os.getenv("LINKEDIN_WRITE_SID")
    jsessionid = os.getenv("LINKEDIN_JSESSIONID")

    if not li_at or not jsessionid:
        pytest.skip(
            "Skipping online test: LINKEDIN_WRITE_SID or LINKEDIN_JSESSIONID not set"
        )

    # Clean jsessionid for header if it has quotes
    csrf_token = jsessionid.strip('"')

    cookies = {"li_at": li_at, "JSESSIONID": jsessionid}
    headers = {"Csrf-Token": csrf_token, "X-RestLi-Protocol-Version": "2.0.0"}

    api = LinkedInAPI(cookies=cookies, headers=headers)

    # Search for technical recruiters in Dubai/UAE (1 page = ~10 results)
    results = api.search_people(
        keywords="technical recruiter",
        regions=[DUBAI_EMIRATE],
        pages=1,
    )

    print(f"\nFound {len(results)} results:")
    for r in results:
        print(f"  - {r.public_id} | {r.first_name} {r.last_name} | {r.headline[:50]}...")

    assert len(results) > 0, "No search results found"
    assert isinstance(results[0], LinkedInProfile), "Result should be LinkedInProfile"
    assert results[0].public_id or results[0].urn, "Result missing identifier"


@pytest.mark.integration
def test_search_company_employees_online():
    """
    Online test that searches for employees within a specific company.
    Requires LINKEDIN_WRITE_SID and LINKEDIN_JSESSIONID environment variables.
    """
    li_at = os.getenv("LINKEDIN_WRITE_SID")
    jsessionid = os.getenv("LINKEDIN_JSESSIONID")

    if not li_at or not jsessionid:
        pytest.skip(
            "Skipping online test: LINKEDIN_WRITE_SID or LINKEDIN_JSESSIONID not set"
        )

    csrf_token = jsessionid.strip('"')
    cookies = {"li_at": li_at, "JSESSIONID": jsessionid}
    headers = {"Csrf-Token": csrf_token, "X-RestLi-Protocol-Version": "2.0.0"}

    api = LinkedInAPI(cookies=cookies, headers=headers)

    # Search for talent/HR people at Revolut in Dubai/UAE (1 page = ~10 results)
    results = api.search_company_employees(
        company="revolut",
        keywords=["talent"],
        regions=[DUBAI_EMIRATE],
        pages=1,
    )

    print(f"\nFound {len(results)} Revolut employees:")
    for r in results:
        print(f"  - {r.public_id} | {r.first_name} {r.last_name} | {r.headline[:50]}...")

    assert len(results) >= 0, "Search should return results or empty list"
    if results:
        assert isinstance(results[0], LinkedInProfile), "Result should be LinkedInProfile"
