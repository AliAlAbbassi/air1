import json
import os

import pytest
from dotenv import load_dotenv

from air1.services.outreach.linkedin_api import LinkedInAPI
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
