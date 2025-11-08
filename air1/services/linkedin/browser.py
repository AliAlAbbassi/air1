from playwright._impl._api_structures import SetCookieParam
from playwright.sync_api import Browser, Page
from .models import LinkedinProfile, CompanyPeople


class BrowserSession:
    def __init__(self, browser: Browser, linkedin_sid: str):
        self.browser = browser
        self.linkedin_sid = linkedin_sid

    def _setup_page(self, url: str) -> Page:
        """Set up a new page with authentication cookies"""
        page = self.browser.new_page()
        page.set_default_timeout(60000)

        if self.linkedin_sid:
            cookies: SetCookieParam = {
                "name": "li_at",
                "value": self.linkedin_sid,
                "domain": ".linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Lax"
            }
            page.context.add_cookies([cookies])

        page.goto(url, timeout=60000)
        return page

    def get_profile_info(self, profile_id: str) -> LinkedinProfile:
        """
        Get LinkedIn profile info from a profile ID

        Args:
            profile_id (str): LinkedIn profile ID (e.g., '')

        Returns:
            LinkedinProfile: Complete profile information
        """
        profile_url = f"https://www.linkedin.com/in/{profile_id}"
        page = self._setup_page(profile_url)

        try:

            profile_data = {}

            # Get name - wait for the h1 to appear
            try:
                name_locator = page.locator("h1.UXwXGvkZjLHXTkTzfStIRtZBcIdwKURDfTbmzc").first
                name_locator.wait_for(timeout=10000)
                name = name_locator.text_content()
                if name:
                    full_name = name.strip()
                    name_parts = full_name.split()
                    profile_data["full_name"] = full_name
                    profile_data["first_name"] = name_parts[0] if name_parts else ""
                    profile_data["last_name"] = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            except:
                pass

            # Get headline
            try:
                headline = page.locator(
                    ".text-body-medium.break-words[data-generated-suggestion-target]").first.text_content()
                if headline:
                    profile_data["headline"] = headline.strip()
            except:
                pass

            # Get location
            try:
                location = page.locator("span.text-body-small.inline.t-black--light.break-words").first.text_content()
                if location:
                    profile_data["location"] = location.strip()
            except:
                pass

            # Click contact info to get email and phone
            try:
                contact_button = page.locator('a[href*="/overlay/contact-info/"]')
                if contact_button.count() > 0:
                    contact_button.click()
                    # Wait for the contact modal to appear
                    page.locator('.pv-contact-info__contact-type').first.wait_for(timeout=5000)

                # Get email
                email_element = page.locator('a[href^="mailto:"]').first
                if email_element.count() > 0:
                    email_href = email_element.get_attribute('href')
                    if email_href and email_href.startswith('mailto:'):
                        profile_data['email'] = email_href.replace('mailto:', '').strip()

                # Get phone
                phone_element = page.locator(
                    '.pv-contact-info__contact-type:has-text("Phone") span.t-14.t-black.t-normal').first
                if phone_element.count() > 0:
                    phone_text = phone_element.text_content()
                    if phone_text:
                        profile_data['phone_number'] = phone_text.strip()

            except Exception as e:
                print(f"Error extracting contact info: {e}")

            return LinkedinProfile(**profile_data)

        except Exception as e:
            print(f"Error scraping profile: {str(e)}")
            return LinkedinProfile()
        finally:
            page.close()

    def get_company_members(self, company_id: str, limit=10) -> CompanyPeople:
        """
        Get all profile IDs of people working at a company

        Args:
            company_id (str): LinkedIn company ID (e.g., 'oreyeon')

        Returns:
            CompanyPeople: Set of profile IDs
        """
        company_url = f"https://www.linkedin.com/company/{company_id}/people/"
        page = self._setup_page(company_url)

        try:

            # Wait for the people cards to load
            page.locator('.org-people-profile-card__profile-card-spacing').first.wait_for(timeout=10000)

            profile_ids = set()
            clicks = 0

            while clicks < limit:
                # Extract profile IDs from current page
                profile_links = page.locator('a[href*="/in/"]').all()

                for link in profile_links:
                    href = link.get_attribute('href')
                    if href and '/in/' in href:
                        # Extract profile ID from URL like "https://www.linkedin.com/in/farahshehab?..."
                        profile_id = href.split('/in/')[1].split('?')[0]
                        if profile_id:
                            profile_ids.add(profile_id)

                # Try to click "Show more results" button
                show_more_button = page.locator('button:has-text("Show more results")').first
                if show_more_button.count() > 0 and show_more_button.is_visible():
                    show_more_button.click()
                    clicks += 1
                    # Wait for new content to load
                    page.wait_for_timeout(2000)
                else:
                    # No more results
                    break

            print(f"Found {len(profile_ids)} profiles for company {company_id}")
            return CompanyPeople(profile_ids=profile_ids)

        except Exception as e:
            print(f"Error scraping company profiles: {str(e)}")
            return CompanyPeople(profile_ids=set())
        finally:
            page.close()
