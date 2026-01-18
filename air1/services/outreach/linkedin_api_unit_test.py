import json
import pytest
from unittest.mock import MagicMock, patch
from air1.services.outreach.linkedin_api import LinkedInAPI

# Mock HTML content for testing get_profile_urn
MOCK_PROFILE_HTML_MEMBER = """
<html>
<body>
    <code>
    "input": {
        "objectUrn": "urn:li:member:12345",
        "publicIdentifier": "test-user"
    },
    "trackingId": "test_tracking_id_123"
    </code>
</body>
</html>
"""

MOCK_PROFILE_HTML_FSD = """
<html>
<body>
    <code>
    "urn:li:fsd_profile:ACoAAB12345",
    "publicIdentifier": "test-user-fsd"
    </code>
    <script>
    "trackingId": "fsd_tracking_id_456"
    </script>
</body>
</html>
"""

MOCK_PROFILE_HTML_NO_TRACKING = """
<html>
<body>
    "objectUrn": "urn:li:member:98765"
    "publicIdentifier": "user-no-tracking"
</body>
</html>
"""

MOCK_PROFILE_HTML_LOGGED_IN_USER = """
<html>
<body>
    "me": "urn:li:fsd_profile:MYSELF123"
    "objectUrn": "urn:li:member:55555"
    "publicIdentifier": "target-user"
    "trackingId": "target_tracking_id"
</body>
</html>
"""

@pytest.fixture
def api():
    return LinkedInAPI(cookies={"li_at": "mock_cookie", "JSESSIONID": "mock_session"})

class TestLinkedInAPIUnit:
    
    @patch('air1.services.outreach.linkedin_api.requests.Session.get')
    def test_get_profile_urn_member_id(self, mock_get, api):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_PROFILE_HTML_MEMBER
        mock_get.return_value = mock_response

        # Execute
        urn, tracking_id = api.get_profile_urn("test-user")

        # Verify
        assert urn == "urn:li:member:12345"
        assert tracking_id == "test_tracking_id_123"
        
    @patch('air1.services.outreach.linkedin_api.requests.Session.get')
    def test_get_profile_urn_fsd_profile(self, mock_get, api):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_PROFILE_HTML_FSD
        mock_get.return_value = mock_response

        # Execute
        urn, tracking_id = api.get_profile_urn("test-user-fsd")

        # Verify
        assert urn == "urn:li:fsd_profile:ACoAAB12345"
        assert tracking_id == "fsd_tracking_id_456"

    @patch('air1.services.outreach.linkedin_api.requests.Session.get')
    def test_get_profile_urn_no_tracking(self, mock_get, api):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_PROFILE_HTML_NO_TRACKING
        mock_get.return_value = mock_response

        # Execute
        urn, tracking_id = api.get_profile_urn("user-no-tracking")

        # Verify
        assert urn == "urn:li:member:98765"
        assert tracking_id is None

    @patch('air1.services.outreach.linkedin_api.requests.Session.post')
    def test_send_connection_request_success(self, mock_post, api):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        # Execute
        result = api.send_connection_request(
            "urn:li:member:12345", 
            message="Hello", 
            tracking_id="track123"
        )

        # Verify
        assert result is True
        
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/growth/normInvitations")
        payload = json.loads(kwargs['data'])
        
        # Verify Payload Structure
        assert payload['emberEntityName'] == "growth/invitation/norm-invitation"
        assert payload['invitee']['com.linkedin.voyager.growth.invitation.InviteeProfile']['profileId'] == "12345"
        assert payload['message'] == "Hello"
        assert payload['trackingId'] == "track123"

    @patch('air1.services.outreach.linkedin_api.requests.Session.post')
    def test_send_connection_request_duplicate_422(self, mock_post, api):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Unprocessable Entity"
        mock_post.return_value = mock_response

        # Execute
        result = api.send_connection_request("urn:li:member:12345")

        # Verify
        assert result is True # Should treat as success due to our recent change

    @patch('air1.services.outreach.linkedin_api.requests.Session.post')
    def test_send_connection_request_failure_400(self, mock_post, api):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        # Execute
        result = api.send_connection_request("urn:li:member:12345")

        # Verify
        assert result is False
