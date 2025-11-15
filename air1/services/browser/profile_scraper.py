from playwright.async_api import Page
from .linkedin_profile import LinkedinProfile
import re


class ProfileScraper:
    """Handles LinkedIn profile data extraction from page"""

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
            except Exception:
                continue
        return False

    @staticmethod
    async def _extract_headline(page: Page, profile_data: dict):
        """Extract headline from profile page"""
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
                        return
        except Exception:
            pass

    @staticmethod
    async def _extract_location(page: Page, profile_data: dict):
        """Extract location from profile page"""
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
                        return
        except Exception:
            pass

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
                except Exception:
                    pass
        except Exception:
            pass

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
        except Exception:
            pass

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
        except Exception:
            pass
