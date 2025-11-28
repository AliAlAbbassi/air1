import re

from loguru import logger
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .linkedin_profile import LinkedinProfile, ProfileExperience

# Exception handling note:
# We catch AttributeError alongside PlaywrightTimeoutError because Playwright locator
# operations can raise AttributeError when elements are detached from the DOM or when
# accessing properties on None results. This is expected behavior when scraping dynamic
# pages where elements may not exist or may disappear during extraction.


class ProfileScraper:
    """Handles LinkedIn profile data extraction from page.

    This scraper tries multiple CSS selectors for each field and gracefully handles
    failures. Expected errors (timeouts, missing elements) are logged at debug level
    and silently skipped. Unexpected errors are logged at warning level but also
    skipped to allow partial data extraction.
    """

    @staticmethod
    async def extract_profile_data(page: Page) -> LinkedinProfile:
        """Extract profile data from LinkedIn profile page"""
        await page.wait_for_timeout(2000)

        profile_data = {}

        name_found = await ProfileScraper._extract_name(page, profile_data)
        if not name_found:
            profile_data.update({"full_name": "", "first_name": "", "last_name": ""})

        await ProfileScraper._extract_headline(page, profile_data)
        await ProfileScraper._extract_location(page, profile_data)
        await ProfileScraper._extract_contact_info(page, profile_data)

        # Extract experience data as part of profile
        experiences = await ProfileScraper.extract_profile_experience(page)
        profile_data["experiences"] = experiences

        return LinkedinProfile(**profile_data)

    @staticmethod
    async def _extract_name(page: Page, profile_data: dict) -> bool:
        """Extract name from profile page"""
        name_selectors = [
            "h1",
            "h1.text-heading-xlarge",
            "main section:first-child h1",
        ]

        for selector in name_selectors:
            try:
                elements = await page.locator(selector).all()
                for elem in elements:
                    name = await elem.text_content()
                    if name and name.strip():
                        full_name = name.strip()
                        name_parts = full_name.split()
                        profile_data["full_name"] = full_name
                        profile_data["first_name"] = name_parts[0] if name_parts else ""
                        profile_data["last_name"] = (
                            " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                        )
                        return True
            except (PlaywrightTimeoutError, AttributeError) as e:
                logger.debug(f"Selector {selector} failed for name extraction: {e}")
                continue
            except Exception as e:
                logger.warning(
                    f"Unexpected error extracting name with selector {selector}: {e}"
                )
                continue
        return False

    @staticmethod
    async def _extract_headline(page: Page, profile_data: dict):
        """Extract headline from profile page"""
        headline_selectors = [
            ".text-body-medium.break-words",
            "div.text-body-medium",
        ]
        for selector in headline_selectors:
            try:
                elements = await page.locator(selector).all()
                for elem in elements:
                    headline = await elem.text_content()
                    if headline and headline.strip() and "headline" not in profile_data:
                        profile_data["headline"] = headline.strip()
                        return
            except (PlaywrightTimeoutError, AttributeError) as e:
                logger.debug(f"Selector {selector} failed for headline extraction: {e}")
                continue
            except Exception as e:
                logger.warning(
                    f"Unexpected error extracting headline with selector {selector}: {e}"
                )
                continue

    @staticmethod
    async def _extract_location(page: Page, profile_data: dict):
        """Extract location from profile page"""
        location_selectors = [
            "span.text-body-small",
            "span:has-text('Located in')",
        ]
        for selector in location_selectors:
            try:
                elements = await page.locator(selector).all()
                for elem in elements:
                    location = await elem.text_content()
                    if location and location.strip() and "location" not in profile_data:
                        profile_data["location"] = location.strip()
                        return
            except (PlaywrightTimeoutError, AttributeError) as e:
                logger.debug(f"Selector {selector} failed for location extraction: {e}")
                continue
            except Exception as e:
                logger.warning(
                    f"Unexpected error extracting location with selector {selector}: {e}"
                )
                continue

    @staticmethod
    async def _extract_contact_info(page: Page, profile_data: dict):
        """Extract contact information from profile page"""
        try:
            contact_button = page.locator('a[href*="/overlay/contact-info/"]')
            if await contact_button.count() > 0:
                await contact_button.click()
                await page.wait_for_timeout(2000)

                await ProfileScraper._extract_email(page, profile_data)

                await ProfileScraper._extract_phone(page, profile_data)

                try:
                    close_button = page.locator('button[aria-label="Dismiss"]')
                    if await close_button.count() > 0:
                        await close_button.click()
                except (PlaywrightTimeoutError, AttributeError) as e:
                    logger.debug(f"Failed to close contact info modal: {e}")
                except Exception as e:
                    logger.warning(f"Unexpected error closing contact info modal: {e}")
        except (PlaywrightTimeoutError, AttributeError) as e:
            logger.debug(f"Failed to extract contact info: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error extracting contact info: {e}")

    @staticmethod
    async def _extract_email(page: Page, profile_data: dict):
        """Extract email from contact info modal"""
        try:
            email_elements = await page.locator('a[href^="mailto:"]').all()
            for elem in email_elements:
                email_href = await elem.get_attribute("href")
                if email_href and "mailto:" in email_href:
                    email = email_href.replace("mailto:", "").split("?")[0].strip()
                    profile_data["email"] = email
                    return
        except (PlaywrightTimeoutError, AttributeError) as e:
            logger.debug(f"Failed to extract email: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error extracting email: {e}")

    @staticmethod
    async def _extract_phone(page: Page, profile_data: dict):
        """Extract phone number from contact info modal"""
        try:
            phone_pattern = r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,5}[-\s\.]?[0-9]{3,5}"

            all_text_elements = await page.locator("span, div").all()
            for elem in all_text_elements:
                text = await elem.text_content()
                if text:
                    matches = re.findall(phone_pattern, text)
                    if matches:
                        profile_data["phone_number"] = matches[0].strip()
                        return
        except (PlaywrightTimeoutError, AttributeError) as e:
            logger.debug(f"Failed to extract phone: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error extracting phone: {e}")

    @staticmethod
    async def extract_profile_experience(page: Page) -> list[ProfileExperience]:
        """Extract work experience data from LinkedIn profile page.

        Args:
            page: Playwright page instance on a LinkedIn profile

        Returns:
            List of ProfileExperience objects with title, company_id, and start_date
        """
        experiences: list[ProfileExperience] = []

        try:
            # Wait for experience section to load - look for the experience entity divs
            experience_selector = 'div[data-view-name="profile-component-entity"]:has(a[href*="/company/"])'
            try:
                await page.wait_for_selector(experience_selector, timeout=10000)
            except Exception:
                # Experience section might not exist or need scrolling
                await page.evaluate("window.scrollBy(0, 1000)")
                try:
                    await page.wait_for_selector(experience_selector, timeout=5000)
                except Exception:
                    logger.debug("No experience section found after scrolling")
                    return experiences

            # Find experience items directly using data-view-name attribute
            # Each experience entry has data-view-name="profile-component-entity"
            # and contains a link to /company/
            experience_items = await page.locator(experience_selector).all()

            logger.debug(f"Found {len(experience_items)} experience items")

            for item in experience_items:
                try:
                    experience = await ProfileScraper._parse_experience_item(item)
                    if experience and (experience.title or experience.company_id):
                        experiences.append(experience)
                except (PlaywrightTimeoutError, AttributeError) as e:
                    logger.debug(f"Failed to parse experience item: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error parsing experience item: {e}")
                    continue

        except (PlaywrightTimeoutError, AttributeError) as e:
            logger.debug(f"Failed to extract experience: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error extracting experience: {e}")

        logger.info(f"Extracted {len(experiences)} experience entries")
        return experiences

    @staticmethod
    async def _parse_experience_item(item) -> ProfileExperience | None:
        """Parse a single experience item element.

        Args:
            item: Playwright locator for an experience list item

        Returns:
            ProfileExperience object or None if parsing fails
        """
        title = ""
        company_id = None
        start_date = None

        # Extract title from div with t-bold class containing span with aria-hidden
        # Structure: <div class="...t-bold"><span aria-hidden="true">Title</span></div>
        title_selectors = [
            'div.t-bold span[aria-hidden="true"]',
            '.hoverable-link-text.t-bold span[aria-hidden="true"]',
            '.mr1.t-bold span[aria-hidden="true"]',
        ]

        for selector in title_selectors:
            try:
                title_elem = item.locator(selector).first
                if await title_elem.count() > 0:
                    title_text = await title_elem.text_content()
                    if title_text and title_text.strip():
                        title = title_text.strip()
                        break
            except Exception:
                continue

        # Extract company ID from link href
        # Links look like: href="https://www.linkedin.com/company/1113019/"
        try:
            company_link = item.locator('a[href*="/company/"]').first
            if await company_link.count() > 0:
                href = await company_link.get_attribute("href")
                if href:
                    match = re.search(r"/company/([^/]+)/?", href)
                    if match:
                        company_id = match.group(1)
        except Exception as e:
            logger.debug(f"Failed to extract company ID: {e}")

        # Extract start date from pvs-entity__caption-wrapper
        # Structure: <span class="pvs-entity__caption-wrapper" aria-hidden="true">Jan 2025 - Present · 11 mos</span>
        date_selectors = [
            'span.pvs-entity__caption-wrapper[aria-hidden="true"]',
            "span.pvs-entity__caption-wrapper",
            ".t-black--light span[aria-hidden='true']",
        ]

        for selector in date_selectors:
            try:
                date_elem = item.locator(selector).first
                if await date_elem.count() > 0:
                    date_text = await date_elem.text_content()
                    if date_text:
                        date_text = date_text.strip()
                        # Match patterns like "Jan 2025", "Feb 2023", "2020"
                        date_match = re.search(
                            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+)?\d{4}",
                            date_text,
                            re.IGNORECASE,
                        )
                        if date_match:
                            start_date = date_match.group(0).strip()
                            break
            except Exception:
                continue

        if not title and not company_id:
            return None

        return ProfileExperience(
            title=title, company_id=company_id, start_date=start_date
        )
