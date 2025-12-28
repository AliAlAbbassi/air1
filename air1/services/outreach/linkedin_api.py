import json

import re
import requests

class LinkedInAPI:
    def __init__(self, cookies=None, headers=None):
        self.session = requests.Session()
        if cookies:
            self.session.cookies.update(cookies)
        
        # Default headers to mimic a browser
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-li-lang": "en_US",
            "x-restli-protocol-version": "2.0.0",
            "accept": "*/*"
        })

        if headers:
            self.session.headers.update(headers)
        self.base_url = "https://www.linkedin.com/voyager/api"

    def _fetch(self, uri, params=None, headers=None):
        url = f"{self.base_url}{uri}"
        return self.session.get(url, params=params, headers=headers)

    def _post(self, uri, data=None, params=None, headers=None, allow_redirects=True):
        url = f"{self.base_url}{uri}"
        return self.session.post(url, data=data, params=params, headers=headers, allow_redirects=allow_redirects)

    def _extract_connection_endpoint_info(self, html_text):
        """
        Extract connection request endpoint and additional info from profile HTML.
        Returns dict with endpoint, trackingId, GraphQL query info, and other connection-related data.
        """
        info = {}
        
        # PRIORITY: Look for GraphQL endpoints and query IDs for connection requests
        # LinkedIn uses GraphQL with queryId pattern: /voyager/api/voyagerXXXGraphQL/graphql?queryId=...
        graphql_patterns = [
            # Pattern 1: GraphQL endpoint with connection/invitation queryId
            r'["\'](/voyager/api/voyager[^"\']*GraphQL/graphql[^"\']*queryId=([^"\'&]+)[^"\']*)["\']',
            # Pattern 2: queryId for connection/invitation mutations
            r'queryId["\']:\s*["\']([^"\']*(?:connection|invitation|invite|connect)[^"\']*)["\']',
            # Pattern 3: GraphQL mutation names for connections
            r'(createInvitation|sendInvitation|connectProfile)[^"\']*queryId["\']:\s*["\']([^"\']+)["\']',
            # Pattern 4: In script tags with GraphQL queries
            r'graphql[^"\']*queryId["\']:\s*["\']([^"\']*(?:invitation|connection|connect)[^"\']*)["\']',
        ]
        
        for pattern in graphql_patterns:
            matches = re.findall(pattern, html_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    query_id = match[-1] if match else None
                else:
                    query_id = match
                
                if query_id and ('invitation' in query_id.lower() or 'connection' in query_id.lower() or 'connect' in query_id.lower()):
                    info['graphql_query_id'] = query_id
                    # Try to find the GraphQL endpoint path
                    graphql_endpoint_match = re.search(r'["\'](/voyager/api/voyager[^"\']*GraphQL/graphql)', html_text, re.IGNORECASE)
                    if graphql_endpoint_match:
                        info['graphql_endpoint'] = graphql_endpoint_match.group(1)
                    else:
                        # Default GraphQL endpoint pattern
                        info['graphql_endpoint'] = '/voyager/api/voyagerGrowthGraphQL/graphql'
                    print(f"DEBUG: Found GraphQL queryId for connection: {query_id}")
                    break
            if 'graphql_query_id' in info:
                break
        
        # Look for connection-related API endpoints in the HTML
        # LinkedIn often embeds API endpoint info in script tags, data attributes, or network requests
        # Try to find actual API call patterns
        endpoint_patterns = [
            # Pattern 1: Full API path in JSON/script tags
            r'["\'](/voyager/api/growth/[^"\']+)["\']',
            r'["\'](/growth/[^"\']+)["\']',
            r'["\'](/voyager/api/relationships/[^"\']+)["\']',
            r'["\'](/relationships/[^"\']+)["\']',
            # Pattern 2: In data attributes or URLs
            r'data-api-endpoint=["\']([^"\']*growth[^"\']*invitation[^"\']*)["\']',
            r'data-api-endpoint=["\']([^"\']*relationship[^"\']*invitation[^"\']*)["\']',
            r'apiEndpoint["\']:\s*["\']([^"\']+)["\']',
            # Pattern 3: In network request patterns
            r'normInvitations[^"\'\\s]*',
            r'/growth/normInvitations[^"\'\\s]*',
            r'/growth/invitations[^"\'\\s]*',
            r'/relationships/memberRelationshipV2[^"\'\\s]*',
            r'memberRelationshipV2[^"\'\\s]*',
        ]
        
        for pattern in endpoint_patterns:
            matches = re.findall(pattern, html_text, re.IGNORECASE)
            for match in matches:
                if match and ('growth' in match.lower() or 'invitation' in match.lower() or 'norm' in match.lower() or 'relationship' in match.lower()):
                    # Clean up the endpoint
                    endpoint = match.strip()
                    if not endpoint.startswith('/'):
                        endpoint = '/' + endpoint
                    if not endpoint.startswith('/voyager/api'):
                        endpoint = '/voyager/api' + endpoint if endpoint.startswith('/') else '/voyager/api/' + endpoint
                    info['endpoint'] = endpoint
                    print(f"DEBUG: Found potential endpoint in HTML: {endpoint}")
                    break
            if 'endpoint' in info:
                break
        
        # Extract trackingId (already done in get_profile_urn, but keep for reference)
        tracking_patterns = [
            r'[&quot;"]trackingId[&quot;":\s]+[&quot;"]([a-zA-Z0-9_\-+/=]+)[&quot;"]',
            r'trackingId[&quot;":\s]+[&quot;"]?([a-zA-Z0-9_\-+/=]+)[&quot;"]?',
        ]
        
        for pattern in tracking_patterns:
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                tracking_id = match.group(1)
                if len(tracking_id) >= 3 and tracking_id not in ['true', 'false', 'null', 'undefined', '0', '1']:
                    info['trackingId'] = tracking_id
                    break
        
        return info

    def get_profile_urn(self, public_id):
        """
        Resolves a public profile ID (slug) to a URN and trackingId.
        Example: "alina-mahtab" -> ("urn:li:fsd_profile:ACoAAD...", "trackingId123")
        
        Returns:
            tuple: (urn, tracking_id) or (None, None) if not found
        """
        # Try 1: Search (Blind)
        params = {
            "keywords": public_id,
            "filters": "List(resultType->PEOPLE)",
            "count": 1,
            "origin": "SWITCH_SEARCH_VERTICAL"
        }
        
        res = self._fetch("/search/blended", params=params)
        print(f"DEBUG: get_profile_urn search status: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            try:
                if "elements" in data:
                    for module in data["elements"]:
                        if "elements" in module:
                            for result in module["elements"]:
                                if "publicIdentifier" in result and result["publicIdentifier"] == public_id:
                                    urn = result["targetUrn"]
                                    # Search API doesn't typically provide trackingId
                                    return (urn, None)
                                if "targetUrn" in result and ":fsd_profile:" in result["targetUrn"]:
                                    urn = result["targetUrn"]
                                    return (urn, None)
            except Exception:
                pass

        # Try 2: HTML Page Scraping (Robust Fallback)
        # This works if the user is logged in and allows us to extract trackingId
        print(f"DEBUG: Falling back to HTML scraping for {public_id}")
        html_text = None
        try:
            profile_url = f"https://www.linkedin.com/in/{public_id}/"
            res = self.session.get(profile_url)
            if res.status_code == 200:
                html_text = res.text
                
                # Store HTML for later use in send_connection_request
                self._last_profile_html = html_text
                
                # Helper function to extract trackingId near a found URN
                def extract_tracking_id_near_urn(urn_match_start, urn_match_end, context_window=2000):
                    """Extract trackingId from HTML near where we found the URN."""
                    start = max(0, urn_match_start - context_window)
                    end = min(len(html_text), urn_match_end + context_window)
                    context = html_text[start:end]
                    
                    # Pattern: trackingId can appear as "trackingId":"value" or "trackingId": "value"
                    # Also handle HTML-encoded quotes: &quot;trackingId&quot;:&quot;value&quot;
                    # Try more specific patterns first, then broader ones
                    patterns = [
                        # Pattern 1: "trackingId":"value" (with quotes)
                        r'[&quot;"]trackingId[&quot;":\s]+[&quot;"]([a-zA-Z0-9_\-+/=]+)[&quot;"]',
                        # Pattern 2: "trackingId": "value" (with space)
                        r'[&quot;"]trackingId[&quot;":\s]+\s*[&quot;"]?([a-zA-Z0-9_\-+/=]+)[&quot;"]?',
                        # Pattern 3: trackingId:value (no quotes, colon)
                        r'trackingId[&quot;":\s]+([a-zA-Z0-9_\-+/=]+)',
                        # Pattern 4: trackingId=value (equals sign)
                        r'trackingId[=]([a-zA-Z0-9_\-+/=]+)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, context, re.IGNORECASE)
                        if match:
                            tracking_id = match.group(1)
                            # Filter out common false positives
                            # Allow shorter IDs (some trackingIds can be short)
                            if len(tracking_id) >= 3 and tracking_id not in ['true', 'false', 'null', 'undefined', '0', '1']:
                                # Additional validation: should look like an ID (alphanumeric, base64-like, or hex)
                                if re.match(r'^[a-zA-Z0-9_\-+/=]+$', tracking_id):
                                    return tracking_id
                    
                    # Fallback: search the entire HTML for trackingId (broader search)
                    # This is less precise but might catch it if it's not near the URN
                    global_patterns = [
                        r'[&quot;"]trackingId[&quot;":\s]+[&quot;"]([a-zA-Z0-9_\-+/=]{8,})[&quot;"]',
                        r'trackingId[&quot;":\s]+[&quot;"]?([a-zA-Z0-9_\-+/=]{8,})[&quot;"]?',
                    ]
                    
                    for pattern in global_patterns:
                        match = re.search(pattern, html_text, re.IGNORECASE)
                        if match:
                            tracking_id = match.group(1)
                            if len(tracking_id) >= 8 and tracking_id not in ['true', 'false', 'null', 'undefined']:
                                return tracking_id
                    
                    return None
                
                # PRIORITY: Try to find fsd_profile URN first (this is what successful responses use)
                # Look for fsd_profile URN near the public_id
                fsd_pattern = r'publicIdentifier[&quot;:\s]+[&quot;]?' + re.escape(public_id) + r'[&quot;,\s]+.*?urn:li:fsd_profile:([a-zA-Z0-9_-]+)'
                fsd_match = re.search(fsd_pattern, html_text)
                if not fsd_match:
                    # Try reverse pattern
                    fsd_pattern2 = r'urn:li:fsd_profile:([a-zA-Z0-9_-]+)[&quot;,\s]+.*?publicIdentifier[&quot;:\s]+[&quot;]?' + re.escape(public_id)
                    fsd_match = re.search(fsd_pattern2, html_text)
                if not fsd_match:
                    # Try finding any fsd_profile near public_id context
                    public_id_pos = html_text.find(public_id)
                    if public_id_pos != -1:
                        context_start = max(0, public_id_pos - 1000)
                        context_end = min(len(html_text), public_id_pos + 1000)
                        context = html_text[context_start:context_end]
                        fsd_match = re.search(r'urn:li:fsd_profile:([a-zA-Z0-9_-]+)', context)
                
                if fsd_match:
                    urn = f"urn:li:fsd_profile:{fsd_match.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(fsd_match.start(), fsd_match.end())
                    print(f"DEBUG: Found fsd_profile URN (PRIORITY): {urn}, trackingId: {tracking_id}")
                    return (urn, tracking_id)
                
                # Pattern 1: objectUrn ... publicIdentifier (common in encoded JSON)
                # Look for objectUrn followed by publicIdentifier within a reasonable distance
                # &quot;objectUrn&quot;:&quot;urn:li:member:123&quot; ... &quot;publicIdentifier&quot;:&quot;hrdiksha&quot;
                pattern1 = r'objectUrn[&quot;:\s]+urn:li:member:(\d+)[&quot;,\s]+.*?' + re.escape(public_id) + r'[&quot;]'
                match1 = re.search(pattern1, html_text)
                if match1:
                    urn = f"urn:li:member:{match1.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(match1.start(), match1.end())
                    print(f"DEBUG: Found precise MEMBER URN via regex 1: {urn}, trackingId: {tracking_id}")
                    # Try to also find fsd_profile for this member
                    # Look for fsd_profile in the HTML that might be associated
                    fsd_fallback = re.search(r'urn:li:fsd_profile:([a-zA-Z0-9_-]+)', html_text)
                    if fsd_fallback:
                        fsd_urn = f"urn:li:fsd_profile:{fsd_fallback.group(1)}"
                        print(f"DEBUG: Also found fsd_profile URN: {fsd_urn} - will try both")
                        # Return fsd_profile as it's more likely to work
                        return (fsd_urn, tracking_id)
                    return (urn, tracking_id)
                
                # Pattern 2: publicIdentifier ... objectUrn
                pattern2 = re.escape(public_id) + r'[&quot;,\s]+.*?objectUrn[&quot;:\s]+urn:li:member:(\d+)'
                match2 = re.search(pattern2, html_text)
                if match2:
                    urn = f"urn:li:member:{match2.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(match2.start(), match2.end())
                    print(f"DEBUG: Found precise MEMBER URN via regex 2: {urn}, trackingId: {tracking_id}")
                    # Try to also find fsd_profile
                    fsd_fallback = re.search(r'urn:li:fsd_profile:([a-zA-Z0-9_-]+)', html_text)
                    if fsd_fallback:
                        fsd_urn = f"urn:li:fsd_profile:{fsd_fallback.group(1)}"
                        print(f"DEBUG: Also found fsd_profile URN: {fsd_urn} - will try both")
                        return (fsd_urn, tracking_id)
                    return (urn, tracking_id)
                
                # Fallback: any fsd_profile
                match = re.search(r'urn:li:fsd_profile:([a-zA-Z0-9_-]+)', html_text)
                if match:
                    urn = f"urn:li:fsd_profile:{match.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(match.start(), match.end())
                    print(f"DEBUG: Found fsd_profile URN via scraping: {urn}, trackingId: {tracking_id}")
                    return (urn, tracking_id)
                
                # Last resort member ID (likely to be wrong/self, but maybe better than None)
                match_member = re.search(r'urn:li:member:(\d+)', html_text)
                if match_member:
                    urn = f"urn:li:member:{match_member.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(match_member.start(), match_member.end())
                    print(f"DEBUG: Found generic MEMBER URN via scraping (RISKY): {urn}, trackingId: {tracking_id}")
                    return (urn, tracking_id)

        except Exception as e:
            print(f"DEBUG: Error scraping profile page: {e}")

        print(f"DEBUG: Could not resolve URN for {public_id}")
        return (None, None)

    def send_connection_request(self, profile_urn_id, message=None, tracking_id=None, profile_html=None):
        """
        Sends a connection request to a profile.
        Uses the voyagerRelationshipsDashMemberRelationships endpoint.
        
        Args:
            profile_urn_id: The URN of the profile to connect with (must be fsd_profile URN)
            message: Optional connection message
            tracking_id: Optional tracking ID extracted from profile page (unused currently)
            profile_html: Optional HTML of the profile page (unused currently)
        """
        # Ensure we have an fsd_profile URN
        if not profile_urn_id.startswith("urn:li:fsd_profile:"):
            print(f"ERROR: send_connection_request requires an fsd_profile URN, got: {profile_urn_id}")
            return False
        
        # The correct endpoint and payload format based on browser network inspection
        endpoint = "/voyagerRelationshipsDashMemberRelationships?action=verifyQuotaAndCreateV2&decorationId=com.linkedin.voyager.dash.deco.relationships.InvitationCreationResultWithInvitee-2"
        
        # Build the payload
        payload = {
            "invitee": {
                "inviteeUnion": {
                    "memberProfile": profile_urn_id
                }
            }
        }
        
        # Add custom message if provided
        if message:
            payload["customMessage"] = message
        
        print(f"DEBUG: Sending connection request to {profile_urn_id}")
        print(f"DEBUG: Endpoint: {endpoint}")
        print(f"DEBUG: Payload: {json.dumps(payload, indent=2)}")
        
        res = self._post(
            endpoint,
            data=json.dumps(payload),
            headers={
                "accept": "application/vnd.linkedin.normalized+json+2.1",
                "content-type": "application/json",
            },
        )
        
        print(f"DEBUG: HTTP status: {res.status_code}")
        
        # Parse response
        response_data = None
        try:
            response_data = res.json()
            print(f"DEBUG: Response: {json.dumps(response_data, indent=2)}")
        except (json.JSONDecodeError, ValueError):
            print(f"DEBUG: Response text (not JSON): {res.text[:500]}")
        
        # Check for success - look for invitationUrn in response
        if res.status_code in [200, 201] and response_data:
            if isinstance(response_data, dict) and "data" in response_data:
                data = response_data["data"]
                if isinstance(data, dict):
                    # Check for ActionResponse with value containing invitationUrn
                    if "value" in data and isinstance(data["value"], dict):
                        if "invitationUrn" in data["value"]:
                            invitation_urn = data["value"]["invitationUrn"]
                            print(f"DEBUG: SUCCESS! Connection request sent. Invitation URN: {invitation_urn}")
                            return True
                    # Direct invitationUrn check
                    if "invitationUrn" in data:
                        print(f"DEBUG: SUCCESS! Connection request sent. Invitation URN: {data['invitationUrn']}")
                        return True
        
        # Check for specific error conditions
        if response_data and isinstance(response_data, dict) and "data" in response_data:
            data = response_data["data"]
            if isinstance(data, dict):
                # Check for status code in response
                if "status" in data:
                    status = data["status"]
                    print(f"DEBUG: Response status in data: {status}")
                    if status == 422:
                        print("ERROR: 422 - Unprocessable Entity. The request format may be invalid or you may have hit a rate limit.")
                    elif status == 400:
                        print("ERROR: 400 - Bad Request. The payload format is incorrect.")
                    elif status == 403:
                        print("ERROR: 403 - Forbidden. You may not have permission to connect with this user.")
        
        print(f"DEBUG: Connection request failed")
        return False
