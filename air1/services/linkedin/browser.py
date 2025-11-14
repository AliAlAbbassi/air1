from playwright._impl._api_structures import SetCookieParam
from playwright.async_api import Browser, Page  # Changed to async API
from .linkedin_profile import LinkedinProfile, CompanyPeople


class BrowserSession:
    def __init__(self, browser: Browser, linkedin_sid: str):
        self.browser = browser
        self.linkedin_sid = linkedin_sid
        self.page = None

    async def _setup_page(self, url: str) -> Page:
        """Set up or reuse existing page with authentication cookies"""
        if self.page is None:
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(60000)

            if self.linkedin_sid:
                cookies: SetCookieParam = {
                    "name": "li_at",
                    "value": self.linkedin_sid,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
                await self.page.context.add_cookies([cookies])

        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            error_str = str(e)
            if "ERR_TOO_MANY_REDIRECTS" in error_str:
                raise Exception(
                    "LinkedIn authentication failed. Your session cookie may be expired. "
                    "Please update the 'linkedin_sid' in your .env file with a fresh cookie value."
                )
            elif "Timeout" in error_str:
                raise Exception(
                    f"Failed to load LinkedIn page: {url}\n"
                    "This could be due to:\n"
                    "1. Invalid or expired linkedin_sid cookie in your .env file\n"
                    "2. LinkedIn blocking automated access\n"
                    "3. Network connectivity issues\n"
                    "Please verify your linkedin_sid cookie is valid and try again."
                )
            raise
        return self.page

    async def get_profile_info(self, profile_id: str) -> LinkedinProfile:
        """
        Get LinkedIn profile info from a profile ID

        Args:
            profile_id (str): LinkedIn profile ID (e.g., '')

        Returns:
            LinkedinProfile: Complete profile information
        """
        profile_url = f"https://www.linkedin.com/in/{profile_id}"
        page = await self._setup_page(profile_url)

        # Wait for page to load
        await page.wait_for_timeout(2000)

        try:
            profile_data = {}

            # Try multiple selectors for the name
            name_found = False
            name_selectors = [
                "h1",  # Most generic, likely to work
                "h1.text-heading-xlarge",
                "main section:first-child h1",
            ]

            for selector in name_selectors:
                try:
                    elements = await page.locator(selector).all()
                    for elem in elements:
                        name = await elem.text_content()
                        if name and name.strip() and not name_found:
                            full_name = name.strip()
                            name_parts = full_name.split()
                            profile_data["full_name"] = full_name
                            profile_data["first_name"] = name_parts[0] if name_parts else ""
                            profile_data["last_name"] = (
                                " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            )
                            name_found = True
                            break
                except Exception:
                    continue

            if not name_found:
                # Set defaults
                profile_data["full_name"] = ""
                profile_data["first_name"] = ""
                profile_data["last_name"] = ""

            # Extract headline
            try:
                headline_selectors = [
                    ".text-body-medium.break-words",
                    "div.text-body-medium",
                ]
                for selector in headline_selectors:
                    elements = await page.locator(selector).all()
                    for elem in elements:
                        headline = await elem.text_content()
                        if headline and headline.strip() and "headline" not in profile_data:
                            profile_data["headline"] = headline.strip()
                            break
                    if "headline" in profile_data:
                        break
            except Exception as e:
                print(f"  DEBUG: Headline extraction error: {e}")

            # Extract location
            try:
                location_selectors = [
                    "span.text-body-small",
                    "span:has-text('Located in')",
                ]
                for selector in location_selectors:
                    elements = await page.locator(selector).all()
                    for elem in elements:
                        location = await elem.text_content()
                        if location and location.strip() and "location" not in profile_data:
                            profile_data["location"] = location.strip()
                            break
                    if "location" in profile_data:
                        break
            except Exception as e:
                print(f"  DEBUG: Location extraction error: {e}")

            # Extract contact info
            try:
                contact_button = page.locator('a[href*="/overlay/contact-info/"]')
                if await contact_button.count() > 0:
                    await contact_button.click()
                    await page.wait_for_timeout(2000)

                    # Try to find email
                    email_elements = await page.locator('a[href^="mailto:"]').all()
                    for elem in email_elements:
                        email_href = await elem.get_attribute("href")
                        if email_href and "mailto:" in email_href:
                            email = email_href.replace("mailto:", "").split("?")[0].strip()
                            profile_data["email"] = email
                            break

                    # Try to find phone with multiple approaches
                    phone_found = False

                    # Look for any text that looks like a phone number
                    all_text_elements = await page.locator("span, div").all()
                    for elem in all_text_elements:
                        text = await elem.text_content()
                        if text:
                            # Check if it looks like a phone number
                            import re
                            phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,5}[-\s\.]?[0-9]{3,5}'
                            matches = re.findall(phone_pattern, text)
                            if matches and not phone_found:
                                profile_data["phone_number"] = matches[0].strip()
                                phone_found = True
                                break

                    # Close the modal
                    try:
                        close_button = page.locator('button[aria-label="Dismiss"]')
                        if await close_button.count() > 0:
                            await close_button.click()
                    except:
                        pass
            except Exception:
                pass

            return LinkedinProfile(**profile_data)

        except Exception as e:
            print(f"Error scraping profile: {str(e)}")
            return LinkedinProfile()

    async def get_company_members(self, company_id: str, limit=10) -> CompanyPeople:
        """
        Get all profile IDs of people working at a company

        Args:
            company_id (str): LinkedIn company ID (e.g., 'oreyeon')

        Returns:
            CompanyPeople: Set of profile IDs
        """
        company_url = f"https://www.linkedin.com/company/{company_id}/people/"
        page = await self._setup_page(company_url)

        try:
            await page.locator(
                ".org-people-profile-card__profile-card-spacing"
            ).first.wait_for(timeout=10000)

            profile_ids = set()
            clicks = 0

            while clicks < limit:
                profile_links = await page.locator('a[href*="/in/"]').all()

                for link in profile_links:
                    href = await link.get_attribute("href")
                    if href and "/in/" in href:
                        profile_id = href.split("/in/")[1].split("?")[0]
                        if profile_id:
                            profile_ids.add(profile_id)

                show_more_button = page.locator(
                    'button:has-text("Show more results")'
                ).first
                if await show_more_button.count() > 0 and await show_more_button.is_visible():
                    await show_more_button.click()
                    clicks += 1
                    await page.wait_for_timeout(2000)
                else:
                    break

            print(f"Found {len(profile_ids)} profiles for company {company_id}")
            return CompanyPeople(profile_ids=profile_ids)

        except Exception as e:
            print(f"Error scraping company profiles: {str(e)}")
            return CompanyPeople(profile_ids=set())
