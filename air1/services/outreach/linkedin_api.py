import json
import re
import time

import requests
from pydantic import BaseModel
from requests.exceptions import ConnectionError, Timeout


class LinkedInProfile(BaseModel):
    """LinkedIn profile from search results or API."""

    public_id: str | None = None
    urn: str | None = None
    first_name: str = ""
    last_name: str = ""
    name: str = ""
    headline: str = ""
    location: str = ""
    about: str = ""
    industry: str = ""
    profile_picture_url: str = ""


class LinkedInJob(BaseModel):
    """Job posting from LinkedIn job search."""

    job_id: str
    title: str = ""
    company_name: str = ""
    company_urn: str | None = None
    location: str = ""
    job_url: str = ""


class LinkedInAPI:
    def __init__(self, cookies=None, headers=None):
        self.session = requests.Session()
        self._csrf_token = None

        if cookies:
            self.session.cookies.update(cookies)
        
        # Default headers to mimic a browser
        self.session.headers.update(
            {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-li-lang": "en_US",
            "x-restli-protocol-version": "2.0.0",
                "accept": "*/*",
            }
        )

        if headers:
            self.session.headers.update(headers)
        self.base_url = "https://www.linkedin.com/voyager/api"

    def _ensure_csrf_token(self, max_retries: int = 3):
        """Fetch and cache the CSRF token from LinkedIn."""
        if self._csrf_token:
            return self._csrf_token

        # The CSRF token is in the JSESSIONID cookie
        # We need to visit LinkedIn first to get it
        jsessionid = self.session.cookies.get("JSESSIONID")

        if not jsessionid:
            # Fetch a page to get the JSESSIONID cookie with retry logic
            for attempt in range(max_retries):
                try:
                    res = self.session.get("https://www.linkedin.com/feed/", timeout=30)
                    jsessionid = self.session.cookies.get("JSESSIONID")
                    break
                except (ConnectionError, Timeout) as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                        time.sleep(wait_time)
                    else:
                        raise e

        if jsessionid:
            # Remove surrounding quotes if present
            self._csrf_token = jsessionid.strip('"')

        return self._csrf_token

    def _fetch(self, uri, params=None, headers=None, max_retries: int = 3):
        url = f"{self.base_url}{uri}"

        # Ensure we have the CSRF token and add it to headers
        csrf_token = self._ensure_csrf_token()
        fetch_headers = headers.copy() if headers else {}
        if csrf_token:
            fetch_headers["csrf-token"] = csrf_token

        for attempt in range(max_retries):
            try:
                return self.session.get(url, params=params, headers=fetch_headers, timeout=30)
            except (ConnectionError, Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
                else:
                    raise e

    def _post(self, uri, data=None, params=None, headers=None, allow_redirects=True):
        url = f"{self.base_url}{uri}"

        # Ensure we have the CSRF token and add it to headers
        csrf_token = self._ensure_csrf_token()
        post_headers = headers.copy() if headers else {}
        if csrf_token:
            post_headers["csrf-token"] = csrf_token

        return self.session.post(
            url,
            data=data,
            params=params,
            headers=post_headers,
            allow_redirects=allow_redirects,
        )

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

                if query_id and (
                    "invitation" in query_id.lower()
                    or "connection" in query_id.lower()
                    or "connect" in query_id.lower()
                ):
                    info["graphql_query_id"] = query_id
                    # Try to find the GraphQL endpoint path
                    graphql_endpoint_match = re.search(
                        r'["\'](/voyager/api/voyager[^"\']*GraphQL/graphql)',
                        html_text,
                        re.IGNORECASE,
                    )
                    if graphql_endpoint_match:
                        info["graphql_endpoint"] = graphql_endpoint_match.group(1)
                    else:
                        # Default GraphQL endpoint pattern
                        info["graphql_endpoint"] = (
                            "/voyager/api/voyagerGrowthGraphQL/graphql"
                        )
                    break
            if "graphql_query_id" in info:
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
                if match and (
                    "growth" in match.lower()
                    or "invitation" in match.lower()
                    or "norm" in match.lower()
                    or "relationship" in match.lower()
                ):
                    # Clean up the endpoint
                    endpoint = match.strip()
                    if not endpoint.startswith("/"):
                        endpoint = "/" + endpoint
                    if not endpoint.startswith("/voyager/api"):
                        endpoint = (
                            "/voyager/api" + endpoint
                            if endpoint.startswith("/")
                            else "/voyager/api/" + endpoint
                        )
                    info["endpoint"] = endpoint
                    break
            if "endpoint" in info:
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
                if len(tracking_id) >= 3 and tracking_id not in [
                    "true",
                    "false",
                    "null",
                    "undefined",
                    "0",
                    "1",
                ]:
                    info["trackingId"] = tracking_id
                    break

        return info

    def get_profile_urn(self, public_id):
        """
        Resolves a public profile ID (slug) to a URN and trackingId.
        Example: "alina-mahtab" -> ("urn:li:fsd_profile:ACoAAD...", "trackingId123")

        Returns:
            tuple: (urn, tracking_id) or (None, None) if not found
        """
        # Ensure we have CSRF token for API calls
        self._ensure_csrf_token()

        # Try 1: GraphQL vanityName endpoint (MOST RELIABLE)
        # This directly resolves vanityName (public_id) to fsd_profile URN
        # LinkedIn uses two query IDs for profile lookup - try both
        graphql_url = "https://www.linkedin.com/voyager/api/graphql"
        query_ids = [
            "voyagerIdentityDashProfiles.2ca312bdbe80fac72fd663a3e06a83e7",
            "voyagerIdentityDashProfiles.a1a483e719b20537a256b6853cdca711",
        ]

        for query_id in query_ids:
            # Build URL manually to avoid URL encoding issues
            # LinkedIn uses a specific format: (vanityName:username) without quotes
            full_url = f"{graphql_url}?includeWebMetadata=true&variables=(vanityName:{public_id})&queryId={query_id}"
            
            # Add CSRF token header for the request
            csrf_token = self._ensure_csrf_token()
            headers = {"csrf-token": csrf_token} if csrf_token else {}
            
            res = self.session.get(full_url, headers=headers)

            if res.status_code == 200:
                try:
                    data = res.json()
                    
                    # Navigate to: data.identityDashProfilesByMemberIdentity.elements[0]
                    # Note: key can be "elements" or "*elements" depending on response format
                    inner_data = data.get("data", {})
                    profiles_response = inner_data.get("identityDashProfilesByMemberIdentity", {})
                    
                    # Try both key variants: "elements" and "*elements"
                    elements = profiles_response.get("elements", []) or profiles_response.get("*elements", [])
                    if elements and len(elements) > 0:
                        # Elements can be URN strings or objects with entityUrn
                        first_elem = elements[0]
                        if isinstance(first_elem, str) and ":fsd_profile:" in first_elem:
                            return (first_elem, None)
                        elif isinstance(first_elem, dict) and "entityUrn" in first_elem:
                            urn = first_elem["entityUrn"]
                            if ":fsd_profile:" in urn:
                                return (urn, None)
                    
                    # Also check 'included' array for the full profile data
                    included = data.get("included", [])
                    for item in included:
                        if isinstance(item, dict) and "entityUrn" in item:
                            urn = item["entityUrn"]
                            if ":fsd_profile:" in urn:
                                return (urn, None)
                except Exception:
                    pass

        # Try 2: Direct profile API (fallback)
        profile_api_url = f"https://www.linkedin.com/voyager/api/identity/profiles/{public_id}"
        res = self.session.get(profile_api_url)

        if res.status_code == 200:
            try:
                data = res.json()
                # The entityUrn in the response is the fsd_profile URN
                if "entityUrn" in data:
                    urn = data["entityUrn"]
                    # Convert member URN to fsd_profile URN if needed
                    if urn.startswith("urn:li:member:"):
                        member_id = urn.split(":")[-1]
                        urn = f"urn:li:fsd_profile:{member_id}"
                    return (urn, None)
                # Check in 'data' wrapper
                if "data" in data and isinstance(data["data"], dict):
                    if "entityUrn" in data["data"]:
                        urn = data["data"]["entityUrn"]
                        return (urn, None)
            except Exception:
                pass

        # Try 3: Search API (fallback)
        params = {
            "keywords": public_id,
            "filters": "List(resultType->PEOPLE)",
            "count": 1,
            "origin": "SWITCH_SEARCH_VERTICAL",
        }
        
        res = self._fetch("/search/blended", params=params)
        
        if res.status_code == 200:
            data = res.json()
            try:
                if "elements" in data:
                    for module in data["elements"]:
                        if "elements" in module:
                            for result in module["elements"]:
                                if (
                                    "publicIdentifier" in result
                                    and result["publicIdentifier"] == public_id
                                ):
                                    urn = result["targetUrn"]
                                    # Search API doesn't typically provide trackingId
                                    return (urn, None)
                                if (
                                    "targetUrn" in result
                                    and ":fsd_profile:" in result["targetUrn"]
                                ):
                                    urn = result["targetUrn"]
                                    return (urn, None)
            except Exception:
                pass

        # Try 4: HTML Page Scraping (Robust Fallback)
        # This works if the user is logged in and allows us to extract trackingId
        html_text = None
        try:
            profile_url = f"https://www.linkedin.com/in/{public_id}/"
            res = self.session.get(profile_url)
            if res.status_code == 200:
                html_text = res.text

                # Store HTML for later use in send_connection_request
                self._last_profile_html = html_text

                # Helper function to extract trackingId near a found URN
                def extract_tracking_id_near_urn(
                    urn_match_start, urn_match_end, context_window=2000
                ):
                    """Extract trackingId from HTML near where we found the URN."""
                    start = max(0, urn_match_start - context_window)
                    end = min(len(html_text), urn_match_end + context_window)
                    context = html_text[start:end]

                    # Pattern: trackingId can appear as "trackingId":"value" or "trackingId": "value"
                    # Also handle HTML-encoded quotes: &quot;trackingId&quot;:&quot;value&quot;
                    # Try more specific patterns first, then broader ones
                    patterns = [
                        # Pattern 1: "trackingId":"value" (with quotes)
                        r'[&quot;"]trackingId[&quot;"]\s*[:]\s*[&quot;"]([a-zA-Z0-9_\-+/=]+)[&quot;"]',
                        # Pattern 2: "trackingId": "value" (with space)
                        r'[&quot;"]trackingId[&quot;"]\s*[:]\s*[&quot;"]?([a-zA-Z0-9_\-+/=]+)[&quot;"]?',
                        # Pattern 3: trackingId:value (no quotes, colon)
                        r'trackingId\s*[:]\s*([a-zA-Z0-9_\-+/=]+)',
                        # Pattern 4: trackingId=value (equals sign)
                        r"trackingId\s*[=]\s*([a-zA-Z0-9_\-+/=]+)",
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, context, re.IGNORECASE)
                        if match:
                            tracking_id = match.group(1)
                            # Filter out common false positives
                            # Allow shorter IDs (some trackingIds can be short)
                            if len(tracking_id) >= 3 and tracking_id not in [
                                "true",
                                "false",
                                "null",
                                "undefined",
                                "0",
                                "1",
                            ]:
                                # Additional validation: should look like an ID (alphanumeric, base64-like, or hex)
                                if re.match(r"^[a-zA-Z0-9_\-+/=]+$", tracking_id):
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
                            if len(tracking_id) >= 8 and tracking_id not in [
                                "true",
                                "false",
                                "null",
                                "undefined",
                            ]:
                                return tracking_id

                    return None

                # PRIORITY 1: Member URN (Legacy ID) - Most reliable for normInvitations
                # Pattern 1: objectUrn ... publicIdentifier (common in encoded JSON)
                pattern1 = (
                    r"objectUrn[&quot;:\s]+urn:li:member:(\d+)[&quot;,\s]+.*?"
                    + re.escape(public_id)
                    + r"[&quot;]"
                )
                match1 = re.search(pattern1, html_text)
                if match1:
                    urn = f"urn:li:member:{match1.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(
                        match1.start(), match1.end()
                    )
                    return (urn, tracking_id)
                
                # Pattern 2: publicIdentifier ... objectUrn
                pattern2 = (
                    re.escape(public_id)
                    + r"[&quot;,\s]+.*?objectUrn[&quot;:\s]+urn:li:member:(\d+)"
                )
                match2 = re.search(pattern2, html_text)
                if match2:
                    urn = f"urn:li:member:{match2.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(
                        match2.start(), match2.end()
                    )
                    return (urn, tracking_id)

                # PRIORITY 2: FSD Profile URN
                # Look for fsd_profile URN near the public_id
                fsd_pattern = (
                    r"publicIdentifier[&quot;:\s]+[&quot;]?"
                    + re.escape(public_id)
                    + r"[&quot;,\s]+.*?urn:li:fsd_profile:([a-zA-Z0-9_-]+)"
                )
                fsd_match = re.search(fsd_pattern, html_text)
                if not fsd_match:
                    # Try reverse pattern
                    fsd_pattern2 = (
                        r"urn:li:fsd_profile:([a-zA-Z0-9_-]+)[&quot;,\s]+.*?publicIdentifier[&quot;:\s]+[&quot;]?"
                        + re.escape(public_id)
                    )
                    fsd_match = re.search(fsd_pattern2, html_text)
                
                if fsd_match:
                    urn = f"urn:li:fsd_profile:{fsd_match.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(
                        fsd_match.start(), fsd_match.end()
                    )
                    return (urn, tracking_id)

                # Fallback: any fsd_profile (excluding logged-in user if possible)
                all_fsd_matches = list(re.finditer(r"urn:li:fsd_profile:([a-zA-Z0-9_-]+)", html_text))
                for match in all_fsd_matches:
                    urn = f"urn:li:fsd_profile:{match.group(1)}"
                    # Simple check to avoid "me" references or obvious self-refs if we can guess them
                    # For now just take the first one found that isn't obviously wrong
                    tracking_id = extract_tracking_id_near_urn(
                        match.start(), match.end()
                    )
                    return (urn, tracking_id)
                
                # Last resort member ID
                match_member = re.search(r"urn:li:member:(\d+)", html_text)
                if match_member:
                    urn = f"urn:li:member:{match_member.group(1)}"
                    tracking_id = extract_tracking_id_near_urn(
                        match_member.start(), match_member.end()
                    )
                    return (urn, tracking_id)

        except Exception:
            pass

        return (None, None)

    def get_profile(self, public_id: str) -> LinkedInProfile | None:
        """
        Fetch a LinkedIn profile by public ID (username) using the API.

        Args:
            public_id: LinkedIn profile username (e.g., 'john-doe-123')

        Returns:
            LinkedInProfile with profile data, or None if not found
        """
        self._ensure_csrf_token()

        # Use the identity dash profiles endpoint with full decoration
        endpoint = f"/identity/dash/profiles?q=memberIdentity&memberIdentity={public_id}&decorationId=com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-93"
        res = self._fetch(endpoint)

        if res.status_code != 200:
            return None

        try:
            data = res.json()

            # Extract the first profile element
            elements = data.get("elements", [])
            if not elements:
                return None

            profile_data = elements[0]

            # Extract profile fields
            first_name = profile_data.get("firstName", "")
            last_name = profile_data.get("lastName", "")
            headline = profile_data.get("headline", "")
            industry = profile_data.get("industryName", "") or ""
            about = profile_data.get("summary", "") or ""

            # Location can be in different formats
            location = profile_data.get("geoLocationName", "") or profile_data.get("locationName", "") or ""

            # Get URN
            urn = profile_data.get("entityUrn", "")

            return LinkedInProfile(
                public_id=public_id,
                urn=urn,
                first_name=first_name,
                last_name=last_name,
                name=f"{first_name} {last_name}".strip(),
                headline=headline,
                location=location,
                about=about,
                industry=industry,
            )
        except Exception:
            return None

    def send_connection_request(
        self, profile_urn_id, message=None, tracking_id=None, profile_html=None
    ):
        """
        Sends a connection request to a profile.
        Uses the 'normInvitations' endpoint which typically requires the Member ID (integer).

        Args:
            profile_urn_id: The URN of the profile (preferably urn:li:member:123)
            message: Optional connection message
            tracking_id: Optional tracking ID - IMPORTANT for avoiding spam filters
            profile_html: Optional HTML of the profile page (unused currently)
        """
        # Extract the ID from the URN if present
        # e.g., urn:li:member:12345 -> 12345
        profile_id = profile_urn_id
        if ":" in profile_urn_id:
            profile_id = profile_urn_id.split(":")[-1]

        # Use the legacy robust endpoint
        endpoint = "/growth/normInvitations"

        payload = {
            "emberEntityName": "growth/invitation/norm-invitation",
            "invitee": {
                "com.linkedin.voyager.growth.invitation.InviteeProfile": {
                    "profileId": profile_id
                }
            },
        }

        if message:
            payload["message"] = message

        if tracking_id:
            payload["trackingId"] = tracking_id

        res = self._post(
            endpoint,
            data=json.dumps(payload),
            headers={
                "accept": "application/vnd.linkedin.normalized+json+2.1",
                "content-type": "application/json",
            },
        )
        
        # Check for success
        if res.status_code == 201:
            return True
            
        # Parse response for error details
        response_data = None
        try:
            response_data = res.json()
        except Exception:
            pass
            
        print(f"DEBUG: Connection error response: {res.text}")
        
        # 422 usually means "Already Connected" or "Pending Invitation"
        if res.status_code == 422:
            print("WARNING: Connection request returned 422 (Unprocessable Entity). This typically means the invite works but is duplicate/pending.")
            return True

        return False

    _RESULTS_PER_PAGE = 10  # LinkedIn returns ~10 results per page

    def search(
        self,
        params: dict,
        pages: int = 1,
    ) -> list[LinkedInProfile]:
        """
        Generic search function. Returns search results.

        Args:
            params: Search parameters dict with keys:
                - keywords: Search keywords
                - filters: List of filter strings like "resultType->PEOPLE", "geoUrn->123"
            pages: Number of pages to fetch (default 1, ~10 results per page)

        Returns:
            List of LinkedInProfile objects
        """
        self._ensure_csrf_token()

        results = []
        current_start = 0

        for page in range(pages):
            # Build filter list
            filters = params.get("filters", [])

            # Build query parameters
            query_parts = []
            if params.get("keywords"):
                query_parts.append(f"keywords:{params['keywords']}")
            query_parts.append("flagshipSearchIntent:SEARCH_SRP")

            # Build queryParameters list
            query_params_list = []
            for f in filters:
                if "->" in f:
                    key, value = f.split("->", 1)
                    # Handle list values (pipe-separated)
                    if "|" in value:
                        values = value.split("|")
                        query_params_list.append(f"(key:{key},value:List({','.join(values)}))")
                    else:
                        query_params_list.append(f"(key:{key},value:List({value}))")

            if query_params_list:
                query_parts.append(f"queryParameters:List({','.join(query_params_list)})")

            query_parts.append("includeFiltersInResponse:false")
            query_str = ",".join(query_parts)

            variables = f"(start:{current_start},origin:FACETED_SEARCH,query:({query_str}))"

            # GraphQL search endpoint
            graphql_url = "https://www.linkedin.com/voyager/api/graphql"
            query_id = "voyagerSearchDashClusters.b0928897b71bd00a5a7291755dcd64f0"
            full_url = f"{graphql_url}?variables={variables}&queryId={query_id}"

            csrf_token = self._ensure_csrf_token()
            headers = {"csrf-token": csrf_token} if csrf_token else {}

            res = self.session.get(full_url, headers=headers)

            if res.status_code != 200:
                break

            try:
                data = res.json()
                page_results = self._extract_search_results(data)

                if not page_results:
                    break

                results.extend(page_results)
                current_start += len(page_results)

                # If we got fewer results than a typical page, we've hit the end
                if len(page_results) < self._RESULTS_PER_PAGE:
                    break

            except Exception:
                break

        return results

    def search_people(
        self,
        keywords: str | None = None,
        connection_of: str | None = None,
        network_depths: list[str] | None = None,
        current_company: list[str] | None = None,
        past_companies: list[str] | None = None,
        regions: list[str] | None = None,
        industries: list[str] | None = None,
        schools: list[str] | None = None,
        pages: int = 1,
    ) -> list[LinkedInProfile]:
        """
        Search for people on LinkedIn.

        Args:
            keywords: Search keywords (e.g., "technical recruiter")
            connection_of: URN ID of a profile to find connections of
            network_depths: List of network depths ["F" (1st), "S" (2nd), "O" (3rd+)]
            current_company: List of company URN IDs to filter by current company
            past_companies: List of company URN IDs to filter by past companies
            regions: List of geo URN IDs (e.g., ["106204383"] for UAE)
            industries: List of industry URN IDs
            schools: List of school URN IDs
            pages: Number of pages to fetch (default 1, ~10 results per page)

        Returns:
            List of LinkedInProfile objects
        """
        filters = ["resultType->PEOPLE"]

        if connection_of:
            filters.append(f"connectionOf->{connection_of}")
        if network_depths:
            filters.append(f"network->{','.join(network_depths)}")
        if current_company:
            filters.append(f"currentCompany->{'|'.join(current_company)}")
        if past_companies:
            filters.append(f"pastCompany->{'|'.join(past_companies)}")
        if regions:
            filters.append(f"geoUrn->{'|'.join(regions)}")
        if industries:
            filters.append(f"industry->{'|'.join(industries)}")
        if schools:
            filters.append(f"schools->{'|'.join(schools)}")

        params = {"filters": filters}
        if keywords:
            params["keywords"] = keywords

        return self.search(params, pages=pages)

    def search_companies(
        self,
        keywords: str | None = None,
        pages: int = 1,
    ) -> list[LinkedInProfile]:
        """
        Search for companies on LinkedIn.

        Args:
            keywords: Search keywords (e.g., "AI startup")
            pages: Number of pages to fetch (default 1, ~10 results per page)

        Returns:
            List of LinkedInProfile objects (with company info)
        """
        filters = ["resultType->COMPANIES"]
        params = {"filters": filters}
        if keywords:
            params["keywords"] = keywords

        return self.search(params, pages=pages)

    def get_company_urn(self, company_name: str) -> str | None:
        """
        Resolve a company name/slug to its URN ID.

        Args:
            company_name: Company name or URL slug (e.g., "revolut", "google")

        Returns:
            Company URN ID (e.g., "11918617") or None if not found
        """
        self._ensure_csrf_token()

        # Try the company API endpoint first
        company_url = "https://www.linkedin.com/voyager/api/organization/companies"
        params = {
            "decorationId": "com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12",
            "q": "universalName",
            "universalName": company_name,
        }

        csrf_token = self._ensure_csrf_token()
        headers = {"csrf-token": csrf_token} if csrf_token else {}

        res = self.session.get(company_url, params=params, headers=headers)

        if res.status_code == 200:
            try:
                data = res.json()
                elements = data.get("elements", [])
                if elements:
                    # Extract company ID from entityUrn like "urn:li:fs_normalized_company:11918617"
                    entity_urn = elements[0].get("entityUrn", "")
                    if entity_urn:
                        # Return just the ID part
                        return entity_urn.split(":")[-1]
            except Exception:
                pass

        # Fallback: search for the company and get the first result
        results = self.search_companies(keywords=company_name, pages=1)
        if results:
            urn = results[0].urn if results[0].urn else ""
            if urn:
                return urn.split(":")[-1]

        return None

    def search_company_employees(
        self,
        company: str,
        keywords: list[str] | None = None,
        regions: list[str] | None = None,
        pages: int = 1,
    ) -> list[LinkedInProfile]:
        """
        Search for employees within a specific company.

        This replicates the LinkedIn URL pattern:
        /company/{company}/people/?facetGeoRegion={geo}&keywords={keywords}

        Args:
            company: Company name/slug (e.g., "revolut", "google") or company URN ID
            keywords: List of search keywords/titles (joined with OR)
                      e.g., ["talent"], ["software engineer", "data engineer"]
            regions: List of geo URN IDs (e.g., ["106204383"] for UAE)
            pages: Number of pages to fetch (default 1, ~10 results per page)

        Returns:
            List of LinkedInProfile objects

        Example:
            # Search for talent/HR people at Revolut in UAE (2 pages = ~20 results)
            employees = api.search_company_employees(
                company="revolut",
                keywords=["talent"],
                regions=["106204383"],
                pages=2,
            )

            # Search for engineers at Google (5 pages = ~50 results)
            employees = api.search_company_employees(
                company="google",
                keywords=["software engineer", "data engineer"],
                pages=5,
            )
        """
        # Resolve company name to URN ID if needed
        company_id = company
        if not company.isdigit():
            resolved_id = self.get_company_urn(company)
            if resolved_id:
                company_id = resolved_id
            else:
                # If we can't resolve, try using the name directly
                company_id = company

        # Join keywords with OR
        search_keywords = None
        if keywords:
            search_keywords = " OR ".join(keywords)

        # Use search_people with current_company filter
        return self.search_people(
            keywords=search_keywords,
            current_company=[company_id],
            regions=regions,
            pages=pages,
        )

    def _extract_search_results(self, data: dict) -> list[LinkedInProfile]:
        """
        Extract profile/entity information from search API response.
        """
        results = []

        try:
            inner_data = data.get("data", {})
            clusters = inner_data.get("searchDashClustersByAll", {})
            elements = clusters.get("elements", [])

            for cluster in elements:
                items = cluster.get("items", [])
                for item in items:
                    entity_result = item.get("item", {}).get("entityResult")
                    if not entity_result:
                        continue

                    # Extract common fields
                    title = entity_result.get("title", {})
                    primary_subtitle = entity_result.get("primarySubtitle", {})
                    secondary_subtitle = entity_result.get("secondarySubtitle", {})

                    name_text = title.get("text", "") if isinstance(title, dict) else ""
                    headline_text = (
                        primary_subtitle.get("text", "")
                        if isinstance(primary_subtitle, dict)
                        else ""
                    )
                    location_text = (
                        secondary_subtitle.get("text", "")
                        if isinstance(secondary_subtitle, dict)
                        else ""
                    )

                    urn = entity_result.get("trackingUrn", "")
                    nav_url = entity_result.get("navigationUrl", "")

                    # Extract public_id based on entity type
                    public_id = None
                    if "/in/" in nav_url:
                        # People profile
                        parts = nav_url.split("/in/")
                        if len(parts) > 1:
                            public_id = parts[1].split("?")[0].strip("/")
                    elif "/company/" in nav_url:
                        # Company
                        parts = nav_url.split("/company/")
                        if len(parts) > 1:
                            public_id = parts[1].split("?")[0].strip("/")

                    # Parse first/last name from full name (for people)
                    first_name = ""
                    last_name = ""
                    if name_text and "/in/" in nav_url:
                        parts = name_text.split(" ", 1)
                        first_name = parts[0] if parts else ""
                        last_name = parts[1] if len(parts) > 1 else ""

                    if public_id:
                        results.append(
                            LinkedInProfile(
                                public_id=public_id,
                                urn=urn,
                                first_name=first_name,
                                last_name=last_name,
                                name=name_text,
                                headline=headline_text,
                                location=location_text,
                            )
                        )

        except Exception:
            pass

        return results

    def search_jobs(
        self,
        geo_id: str | None = None,
        keywords: str | None = None,
        pages: int = 1,
    ) -> list[LinkedInJob]:
        """
        Search for job postings and extract company information.

        Args:
            geo_id: LinkedIn geo ID for location filter (e.g., '104305776' for UAE)
            keywords: Job search keywords
            pages: Number of pages to fetch (25 jobs per page)

        Returns:
            List of LinkedInJob objects with company info
        """
        self._ensure_csrf_token()

        all_jobs = []

        for page in range(pages):
            start = page * 25

            # Build the query
            query_parts = ["origin:JOB_SEARCH_PAGE_QUERY_EXPANSION", "spellCorrectionEnabled:true"]

            if geo_id:
                query_parts.append(f"locationUnion:(geoId:{geo_id})")

            if keywords:
                query_parts.append(f"keywords:{keywords}")

            query = f"({','.join(query_parts)})"

            endpoint = (
                f"/voyagerJobsDashJobCards"
                f"?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-186"
                f"&count=25"
                f"&q=jobSearch"
                f"&query={query}"
                f"&start={start}"
            )

            res = self._fetch(endpoint)

            if res.status_code != 200:
                break

            try:
                data = res.json()
                jobs = self._extract_job_results(data)
                all_jobs.extend(jobs)
            except Exception:
                break

        return all_jobs

    def _extract_job_results(self, data: dict) -> list[LinkedInJob]:
        """Extract job posting information from job search API response."""
        results = []

        try:
            elements = data.get("elements", [])

            for elem in elements:
                job_card = elem.get("jobCardUnion", {}).get("jobPostingCard", {})
                if not job_card:
                    continue

                # Extract job ID from entityUrn
                entity_urn = job_card.get("entityUrn", "")
                job_id = ""
                if entity_urn:
                    # Format: urn:li:fsd_jobPostingCard:(4349590584,JOBS_SEARCH)
                    match = re.search(r"\((\d+),", entity_urn)
                    if match:
                        job_id = match.group(1)

                # Extract title
                title = job_card.get("title", {}).get("text", "")

                # Extract company name from primaryDescription
                company_name = job_card.get("primaryDescription", {}).get("text", "")

                # Extract location from secondaryDescription
                location = job_card.get("secondaryDescription", {}).get("text", "")

                # Build job URL
                job_url = f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else ""

                if job_id:
                    results.append(
                        LinkedInJob(
                            job_id=job_id,
                            title=title,
                            company_name=company_name,
                            location=location,
                            job_url=job_url,
                        )
                    )

        except Exception:
            pass

        return results

    def get_companies_from_jobs(
        self,
        geo_id: str | None = None,
        keywords: str | None = None,
        pages: int = 1,
    ) -> list[str]:
        """
        Search jobs and return unique company names.

        Args:
            geo_id: LinkedIn geo ID for location filter
            keywords: Job search keywords
            pages: Number of pages to fetch

        Returns:
            List of unique company names
        """
        jobs = self.search_jobs(geo_id=geo_id, keywords=keywords, pages=pages)
        companies = list({job.company_name for job in jobs if job.company_name})
        return companies
