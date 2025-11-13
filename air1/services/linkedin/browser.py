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

        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
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

        try:
            profile_data = {}

            try:
                name_locator = page.locator(
                    "h1.UXwXGvkZjLHXTkTzfStIRtZBcIdwKURDfTbmzc"
                ).first
                await name_locator.wait_for(timeout=10000)
                name = await name_locator.text_content()
                if name:
                    full_name = name.strip()
                    name_parts = full_name.split()
                    profile_data["full_name"] = full_name
                    profile_data["first_name"] = name_parts[0] if name_parts else ""
                    profile_data["last_name"] = (
                        " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                    )
            except Exception:
                pass

            try:
                headline = await page.locator(
                    ".text-body-medium.break-words[data-generated-suggestion-target]"
                ).first.text_content()
                if headline:
                    profile_data["headline"] = headline.strip()
            except Exception:
                pass

            try:
                location = await page.locator(
                    "span.text-body-small.inline.t-black--light.break-words"
                ).first.text_content()
                if location:
                    profile_data["location"] = location.strip()
            except Exception:
                pass

            try:
                contact_button = page.locator('a[href*="/overlay/contact-info/"]')
                if await contact_button.count() > 0:
                    await contact_button.click()
                    await page.locator(".pv-contact-info__contact-type").first.wait_for(
                        timeout=5000
                    )

                email_element = page.locator('a[href^="mailto:"]').first
                if await email_element.count() > 0:
                    email_href = await email_element.get_attribute("href")
                    if email_href and email_href.startswith("mailto:"):
                        profile_data["email"] = email_href.replace(
                            "mailto:", ""
                        ).strip()

                phone_element = page.locator(
                    '.pv-contact-info__contact-type:has-text("Phone") span.t-14.t-black.t-normal'
                ).first
                if await phone_element.count() > 0:
                    phone_text = await phone_element.text_content()
                    if phone_text:
                        profile_data["phone_number"] = phone_text.strip()

            except Exception as e:
                print(f"Error extracting contact info: {e}")

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
